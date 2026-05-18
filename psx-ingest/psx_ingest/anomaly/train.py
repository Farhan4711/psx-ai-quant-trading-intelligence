"""
Per-symbol IsolationForest trainer.

Trains one model per active symbol on the trailing `lookback_days` of
adjusted OHLCV bars. Serialises with joblib to
`{model_dir}/{symbol}.joblib`. The Celery wrapper in
`psx_ingest/tasks/anomaly.py` runs this nightly.

Why per-symbol rather than one global model?
--------------------------------------------
Volume distributions differ wildly across PSX (a 10× spike on UBL is
routine; on a thinly-traded mid-cap it's a clear anomaly). Per-symbol
trees keep their thresholds calibrated. The cost — 84 model files,
~5KB each — is trivial.

Skipping symbols
----------------
- Fewer than `min_bars` (default 200) bars → no model written; the
  detector falls back to the L2 baseline.
- Constant features (e.g. brand-new listing where volume is zero for
  many days) → sklearn whines and we skip.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.anomaly.features import Bar, FEATURE_ORDER, features_for_bars
from psx_ingest.config import settings

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class TrainSummary:
    symbols_attempted: int = 0
    symbols_trained: int = 0
    symbols_skipped_insufficient_data: int = 0
    symbols_skipped_constant: int = 0
    symbols_failed: int = 0


# ── Disk layout ───────────────────────────────────────────────────


def _default_model_dir() -> Path:
    """`./models/anomaly/` relative to repo root, override-able via env."""
    import os
    override = os.environ.get("PSX_ANOMALY_MODEL_DIR")
    if override:
        return Path(override)
    # repo_root = parent of `psx-ingest/`
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    return repo_root / "models" / "anomaly"


def model_path(symbol: str, model_dir: Path | None = None) -> Path:
    return (model_dir or _default_model_dir()) / f"{symbol}.joblib"


# ── Per-symbol fit ────────────────────────────────────────────────


def fit_one(bars: list[Bar], *, contamination: float = 0.02) -> Any | None:
    """
    Fit a single IsolationForest. Returns the trained model, or None
    if `bars` is too small or the feature matrix is degenerate.

    Imports sklearn lazily so module-level imports of `psx_ingest`
    don't drag a 50MB dependency into the Celery worker startup path
    when the trainer isn't actually being called.
    """
    if len(bars) < 200:
        return None

    matrix = features_for_bars(bars)
    # Skip the first 20 rows — vol_spike isn't defined there.
    matrix = matrix[20:]
    if not matrix:
        return None

    # Drop any rows with NaN/inf (defensive against bad data)
    cleaned = [row for row in matrix if all(_is_finite(v) for v in row)]
    if len(cleaned) < 100:
        return None

    # Check for constant columns — IsolationForest tolerates them but a
    # symbol with constant volume is a bad-data signal we want to log.
    by_col = list(zip(*cleaned))
    for i, col in enumerate(by_col):
        if min(col) == max(col):
            logger.warning(
                "anomaly.constant_column",
                feature=FEATURE_ORDER[i],
                value=col[0],
            )
            return None

    from sklearn.ensemble import IsolationForest  # noqa: PLC0415 (lazy import)

    model = IsolationForest(
        contamination=contamination,
        n_estimators=100,
        max_samples=min(256, len(cleaned)),
        random_state=42,
        n_jobs=1,
    )
    model.fit(cleaned)
    return model


def _is_finite(v: float) -> bool:
    return v == v and v not in (float("inf"), float("-inf"))


def save_model(model: Any, symbol: str, *, model_dir: Path | None = None) -> Path:
    import joblib  # lazy import
    target_dir = model_dir or _default_model_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{symbol}.joblib"
    joblib.dump(
        {
            "model": model,
            "feature_order": list(FEATURE_ORDER),
            "trained_at": date.today().isoformat(),
        },
        path,
    )
    return path


# ── Bulk trainer (called by the Celery task) ─────────────────────


async def _fetch_bars(
    session: AsyncSession, symbol: str, lookback_days: int
) -> list[Bar]:
    cutoff = date.today() - timedelta(days=lookback_days)
    result = await session.execute(
        text(
            """
            SELECT open, high, low, close, volume
            FROM ohlcv_daily
            WHERE symbol = :symbol AND date >= :cutoff
            ORDER BY date ASC
            """
        ),
        {"symbol": symbol, "cutoff": cutoff},
    )
    return [
        Bar(
            open=float(r[0]),
            high=float(r[1]),
            low=float(r[2]),
            close=float(r[3]),
            volume=float(r[4]),
        )
        for r in result.fetchall()
    ]


async def _list_active_symbols(session: AsyncSession) -> list[str]:
    result = await session.execute(
        text("SELECT symbol FROM securities WHERE is_active = TRUE ORDER BY symbol")
    )
    return [r[0] for r in result.fetchall()]


async def train_all(
    *,
    lookback_days: int = 730,  # ~2 years
    model_dir: Path | None = None,
) -> TrainSummary:
    """Train one IsolationForest per active symbol. Returns a summary
    suitable for stuffing into a Celery task result / log line."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    summary = TrainSummary()
    try:
        async with session_factory() as session:
            symbols = await _list_active_symbols(session)
            summary.symbols_attempted = len(symbols)
            for symbol in symbols:
                try:
                    bars = await _fetch_bars(session, symbol, lookback_days)
                    if len(bars) < 200:
                        summary.symbols_skipped_insufficient_data += 1
                        continue
                    model = fit_one(bars)
                    if model is None:
                        summary.symbols_skipped_constant += 1
                        continue
                    save_model(model, symbol, model_dir=model_dir)
                    summary.symbols_trained += 1
                except Exception as exc:
                    summary.symbols_failed += 1
                    logger.error(
                        "anomaly.train_failed", symbol=symbol, error=str(exc)
                    )
    finally:
        await engine.dispose()

    logger.info(
        "anomaly.train_complete",
        attempted=summary.symbols_attempted,
        trained=summary.symbols_trained,
        skipped_data=summary.symbols_skipped_insufficient_data,
        skipped_constant=summary.symbols_skipped_constant,
        failed=summary.symbols_failed,
    )
    return summary


def summary_as_dict(s: TrainSummary) -> dict[str, int]:
    return {
        "symbols_attempted": s.symbols_attempted,
        "symbols_trained": s.symbols_trained,
        "symbols_skipped_insufficient_data": s.symbols_skipped_insufficient_data,
        "symbols_skipped_constant": s.symbols_skipped_constant,
        "symbols_failed": s.symbols_failed,
    }
