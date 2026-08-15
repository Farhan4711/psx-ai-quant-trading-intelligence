"""
Prediction service.

Loads OHLCV + macro context for the requested symbol, computes the feature
vector, runs the heuristic ensemble, and persists the prediction so the
retrain job (Step 46) can reconcile against realised next-day direction
and compute live accuracy.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.macro import MacroIndicator
from psx_api.models.ohlcv import OhlcvDaily
from psx_api.models.predictions import ModelPrediction
from psx_api.models.securities import Security
from psx_api.predictions import ensemble
from psx_api.predictions.features import MarketContext, OhlcvBar, compute_features
from psx_api.timezone import today_pkt


class PredictionError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


# Stocks below this share-volume × close threshold get "predictions
# disabled" — the build plan calls for ranking by avg-daily volume, but
# without backfilled liquidity data we use a simple bar-count proxy.
MIN_BARS_FOR_PREDICTION = 80


class PredictionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def predict(self, symbol: str, *, horizon_days: int = 1) -> dict[str, Any]:
        symbol = symbol.upper().strip()
        sec = (
            await self._db.execute(select(Security).where(Security.symbol == symbol))
        ).scalar_one_or_none()
        if not sec:
            raise PredictionError(f"Unknown symbol '{symbol}'.", status_code=404)

        bars = await self._load_recent_bars(symbol, n=120)
        if len(bars) < MIN_BARS_FOR_PREDICTION:
            return {
                "symbol": symbol,
                "as_of_date": None,
                "predictions_disabled": True,
                "reason": (
                    f"Only {len(bars)} bars of history available — need at least "
                    f"{MIN_BARS_FOR_PREDICTION} for a credible prediction."
                ),
                "model_version": ensemble.MODEL_VERSION,
            }

        # Latest date the OHLCV row pertains to
        as_of = bars[-1]["date"]
        # Convert to feature inputs
        bar_objs = [
            OhlcvBar(
                open=float(b["open"]),
                high=float(b["high"]),
                low=float(b["low"]),
                close=float(b["close"]),
                volume=float(b["volume"] or 0),
            )
            for b in bars
        ]

        context = await self._market_context(sec, as_of)
        features = compute_features(bar_objs, context=context)
        # Pass `symbol` so the ensemble can route to the trained
        # inference service (Phase 12). Falls back to the heuristic
        # silently if the service is unreachable or has no model for
        # this symbol — caller behaviour is unchanged either way.
        result = ensemble.predict(features, symbol=symbol, horizon_days=horizon_days)

        # Persist (best-effort — duplicate (symbol, as_of_date, version)
        # for the same trading day is fine to silently ignore)
        await self._persist(symbol, as_of, result)

        return {
            "symbol": symbol,
            "as_of_date": as_of.isoformat(),
            "horizon_days": horizon_days,
            "probability_up": result.probability_up,
            "confidence": result.confidence,
            "confidence_score": result.confidence_score,
            "model_version": result.model_version,
            "sub_model_probabilities": result.sub_model_probabilities,
            "key_features": [
                {
                    "name": f.name,
                    "value": f.value,
                    "contribution": f.contribution,
                }
                for f in result.top_features
            ],
            "live_accuracy_pct": await self._live_accuracy_pct(symbol, result.model_version),
            "predictions_disabled": False,
        }

    # ── Internals ─────────────────────────────────────────────────────

    async def _load_recent_bars(self, symbol: str, *, n: int) -> list[dict[str, Any]]:
        rows = (
            await self._db.execute(
                select(
                    OhlcvDaily.date,
                    OhlcvDaily.open,
                    OhlcvDaily.high,
                    OhlcvDaily.low,
                    OhlcvDaily.close,
                    OhlcvDaily.volume,
                )
                .where(OhlcvDaily.symbol == symbol)
                .order_by(OhlcvDaily.date.desc())
                .limit(n)
            )
        ).all()
        rows = list(reversed(rows))
        return [
            {
                "date": r[0],
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "volume": r[5],
            }
            for r in rows
        ]

    async def _market_context(self, sec: Security, as_of: date) -> MarketContext:
        # Latest macro snapshots ≤ as_of_date — best-effort, OK if some are missing
        async def latest(name: str) -> Decimal | None:
            row = (
                await self._db.execute(
                    select(MacroIndicator.value)
                    .where(
                        MacroIndicator.indicator == name,
                        MacroIndicator.date <= as_of,
                    )
                    .order_by(MacroIndicator.date.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            return row

        kibor_6m = await latest("kibor_6m")

        # PKR/USD daily change: today vs yesterday
        rows = (
            await self._db.execute(
                select(MacroIndicator.date, MacroIndicator.value)
                .where(
                    MacroIndicator.indicator == "pkr_usd",
                    MacroIndicator.date <= as_of,
                )
                .order_by(MacroIndicator.date.desc())
                .limit(2)
            )
        ).all()
        fx_change_pct: float | None = None
        if len(rows) == 2 and rows[1][1] not in (0, None):
            fx_change_pct = float((rows[0][1] - rows[1][1]) / rows[1][1] * 100)

        return MarketContext(
            kse100_return_pct=None,  # wired in once we have a KSE-100 daily series
            sector_return_pct=None,  # same
            kibor_6m_pct=float(kibor_6m) if kibor_6m is not None else None,
            pkr_usd_change_pct=fx_change_pct,
        )

    async def _persist(self, symbol: str, as_of: date, p: ensemble.Prediction) -> None:
        row = ModelPrediction(
            symbol=symbol,
            model_version=p.model_version,
            as_of_date=as_of,
            horizon_days=p.horizon_days,
            probability_up=Decimal(str(round(p.probability_up, 4))),
            confidence=p.confidence,
            confidence_score=Decimal(str(round(p.confidence_score, 4))),
        )
        self._db.add(row)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()  # already recorded for today — fine

    async def _live_accuracy_pct(self, symbol: str, model_version: str) -> float | None:
        """Rolling 30-day accuracy for this (symbol, model_version)."""
        cutoff = today_pkt() - timedelta(days=30)
        rows = (
            await self._db.execute(
                select(ModelPrediction.probability_up, ModelPrediction.realised_direction).where(
                    ModelPrediction.symbol == symbol,
                    ModelPrediction.model_version == model_version,
                    ModelPrediction.as_of_date >= cutoff,
                    ModelPrediction.realised_direction.is_not(None),
                )
            )
        ).all()
        if len(rows) < 5:
            return None
        correct = 0
        for prob, direction in rows:
            predicted_up = float(prob) >= 0.5
            actual_up = direction == 1
            if predicted_up == actual_up:
                correct += 1
        return round(correct / len(rows) * 100, 1)
