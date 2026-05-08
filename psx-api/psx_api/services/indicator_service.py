"""
Indicator computation service.

Pulls OHLCV history from the DB, runs the requested indicator from
psx_api.indicators.compute, and pairs the latest reading with a
plain-English interpretation. Cached aggressively — values for closed
days never change.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.cache import TTL_OHLCV, cached
from psx_api.indicators import compute, interpret
from psx_api.models.ohlcv import OhlcvDaily

IndicatorKey = Literal[
    "rsi", "macd", "sma50", "sma200", "ema20", "bbands", "stochastic", "obv", "atr"
]


SUPPORTED: list[dict] = [
    {"key": "rsi", "label": "RSI (14)", "category": "momentum"},
    {"key": "macd", "label": "MACD (12, 26, 9)", "category": "momentum"},
    {"key": "sma50", "label": "SMA 50", "category": "trend"},
    {"key": "sma200", "label": "SMA 200", "category": "trend"},
    {"key": "ema20", "label": "EMA 20", "category": "trend"},
    {"key": "bbands", "label": "Bollinger Bands (20, 2σ)", "category": "volatility"},
    {"key": "stochastic", "label": "Stochastic (14, 3)", "category": "momentum"},
    {"key": "obv", "label": "OBV", "category": "volume"},
    {"key": "atr", "label": "ATR (14)", "category": "volatility"},
]


class IndicatorService:
    def __init__(self, db: AsyncSession, redis: Redis | None = None) -> None:  # type: ignore[type-arg]
        self._db = db
        self._redis = redis

    async def compute_indicator(self, symbol: str, indicator: IndicatorKey) -> dict:
        cache_key = f"indicator:{symbol}:{indicator}"

        async def _load() -> dict:
            return await self._compute_uncached(symbol, indicator)

        if self._redis is None:
            return await _load()
        return await cached(self._redis, cache_key, TTL_OHLCV, _load)

    # ------------------------------------------------------------------

    async def _compute_uncached(self, symbol: str, indicator: IndicatorKey) -> dict:
        # Pull last ~250 trading days — enough for SMA-200 with headroom
        rows = (
            await self._db.execute(
                select(
                    OhlcvDaily.date,
                    OhlcvDaily.high,
                    OhlcvDaily.low,
                    OhlcvDaily.close,
                    OhlcvDaily.volume,
                )
                .where(OhlcvDaily.symbol == symbol)
                .order_by(OhlcvDaily.date.desc())
                .limit(260)
            )
        ).all()

        if not rows:
            return {
                "symbol": symbol,
                "indicator": indicator,
                "as_of": None,
                "signal": "neutral",
                "summary": "No price history available for this symbol yet.",
                "explainer": "",
                "value": {},
            }

        # Re-order chronologically (oldest → newest)
        rows = list(reversed(rows))
        dates: list[date] = [r[0] for r in rows]
        highs = [float(r[1]) if r[1] is not None else float("nan") for r in rows]
        lows = [float(r[2]) if r[2] is not None else float("nan") for r in rows]
        closes = [float(r[3]) if r[3] is not None else float("nan") for r in rows]
        volumes = [float(r[4]) if r[4] is not None else 0.0 for r in rows]
        last_close = closes[-1]
        as_of = dates[-1].isoformat()

        if indicator == "rsi":
            series = compute.rsi(closes, period=14)
            res = interpret.interpret_rsi(series[-1])
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "macd":
            d = compute.macd(closes)
            res = interpret.interpret_macd(d["macd"][-1], d["signal"][-1], d["histogram"][-1])
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "sma50":
            series = compute.sma(closes, 50)
            res = interpret.interpret_sma(last_close, series[-1], 50)
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "sma200":
            series = compute.sma(closes, 200)
            res = interpret.interpret_sma(last_close, series[-1], 200)
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "ema20":
            series = compute.ema(closes, 20)
            res = interpret.interpret_ema(last_close, series[-1], 20)
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "bbands":
            d = compute.bollinger_bands(closes)
            res = interpret.interpret_bollinger(
                last_close, d["upper"][-1], d["middle"][-1], d["lower"][-1]
            )
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "stochastic":
            d = compute.stochastic(highs, lows, closes)
            res = interpret.interpret_stochastic(d["k"][-1], d["d"][-1])
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "obv":
            series = compute.obv(closes, volumes)
            week_idx = max(0, len(series) - 6)
            res = interpret.interpret_obv(series[-1], series[week_idx])
            return self._wrap(symbol, indicator, as_of, res)

        if indicator == "atr":
            series = compute.atr(highs, lows, closes, period=14)
            res = interpret.interpret_atr(series[-1], last_close)
            return self._wrap(symbol, indicator, as_of, res)

        raise ValueError(f"Unknown indicator: {indicator}")

    @staticmethod
    def _wrap(symbol: str, indicator: str, as_of: str, res: dict) -> dict:
        return {
            "symbol": symbol,
            "indicator": indicator,
            "as_of": as_of,
            "signal": res["signal"],
            "summary": res["summary"],
            "explainer": res["explainer"],
            "value": res["value"],
        }
