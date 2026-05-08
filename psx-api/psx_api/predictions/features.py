"""
Pure-Python feature engineering for the prediction layer.

Given a list of OHLCV bars (oldest → newest) and optional same-day market
context (KSE-100 return, sector return, KIBOR, FX), compute the feature
vector the build plan calls for in Step 41:

  - Log returns (1, 5, 10, 20-day)
  - RSI(14), Stochastic %K(14)
  - MACD line / signal / histogram (12, 26, 9)
  - Bollinger %B (20, 2σ)        — distance of close inside the bands
  - Williams %R(14)
  - Momentum(10)                  — close / close[-10] - 1
  - Disparity 5, Disparity 10     — close / SMA(n) - 1
  - ATR(14) / close               — volatility normalised by price
  - OBV change                    — OBV today vs OBV 5 days ago
  - Volume Z-score (vs 20-day mean)
  - Price Z-score (vs 50-day mean)
  - Market context: KSE-100 same-day return, sector same-day return
  - Macro context: KIBOR 6M level, PKR/USD daily change

The function returns a flat dict[str, float|None]. None means the
warm-up period for that feature isn't satisfied yet — downstream models
must handle this (drop / impute / mask).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from typing import Sequence

from psx_api.indicators import compute


# ── Inputs ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MarketContext:
    """Optional daily macro/market context aligned to the latest bar."""

    kse100_return_pct: float | None = None
    sector_return_pct: float | None = None
    kibor_6m_pct: float | None = None
    pkr_usd_change_pct: float | None = None


@dataclass(frozen=True)
class OhlcvBar:
    open: float
    high: float
    low: float
    close: float
    volume: float


# ── Helpers ─────────────────────────────────────────────────────────────


def _safe_log_return(prev: float, curr: float) -> float | None:
    if prev is None or curr is None or prev <= 0 or curr <= 0:
        return None
    return log(curr / prev)


def _z_score(values: Sequence[float], current: float) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
    std = sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    return (current - mean) / std


# ── Public API ──────────────────────────────────────────────────────────


def compute_features(
    bars: Sequence[OhlcvBar], context: MarketContext | None = None
) -> dict[str, float | None]:
    """
    Returns the latest-bar feature dict. `bars` should be at least 60
    long for the full feature set; shorter histories will return None
    for the longer-window features.
    """
    if not bars:
        return {}

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    n = len(closes)
    last = closes[-1]

    out: dict[str, float | None] = {}

    # ── Log returns ─────────────────────────────────────────────
    for k in (1, 5, 10, 20):
        if n > k:
            out[f"log_return_{k}d"] = _safe_log_return(closes[-1 - k], closes[-1])
        else:
            out[f"log_return_{k}d"] = None

    # ── Momentum & Disparity ────────────────────────────────────
    out["momentum_10"] = (last / closes[-11] - 1) if n > 10 and closes[-11] > 0 else None

    sma5 = compute.sma(closes, 5)[-1]
    sma10 = compute.sma(closes, 10)[-1]
    out["disparity_5"] = (last / sma5 - 1) if sma5 else None
    out["disparity_10"] = (last / sma10 - 1) if sma10 else None

    # ── RSI / Stochastic / Williams %R ─────────────────────────
    out["rsi_14"] = compute.rsi(closes, 14)[-1]
    stoch = compute.stochastic(highs, lows, closes, k_period=14, d_period=3)
    out["stochastic_k"] = stoch["k"][-1]
    out["stochastic_d"] = stoch["d"][-1]

    if n >= 14:
        win_high = max(highs[-14:])
        win_low = min(lows[-14:])
        denom = win_high - win_low
        out["williams_r_14"] = (
            -100 * (win_high - last) / denom if denom != 0 else 0.0
        )
    else:
        out["williams_r_14"] = None

    # ── MACD ────────────────────────────────────────────────────
    macd = compute.macd(closes, fast=12, slow=26, signal_period=9)
    out["macd"] = macd["macd"][-1]
    out["macd_signal"] = macd["signal"][-1]
    out["macd_histogram"] = macd["histogram"][-1]

    # ── Bollinger %B ────────────────────────────────────────────
    bb = compute.bollinger_bands(closes, period=20, num_std=2.0)
    upper, lower = bb["upper"][-1], bb["lower"][-1]
    if upper is not None and lower is not None and upper != lower:
        out["bollinger_pct_b"] = (last - lower) / (upper - lower)
    else:
        out["bollinger_pct_b"] = None

    # ── ATR / price ─────────────────────────────────────────────
    atr14 = compute.atr(highs, lows, closes, period=14)[-1]
    out["atr_14_norm"] = (atr14 / last) if atr14 is not None and last > 0 else None

    # ── OBV change (today vs 5 days ago) ────────────────────────
    obv_series = compute.obv(closes, volumes)
    if n >= 6 and obv_series[-1] is not None and obv_series[-6] is not None:
        prev_obv = obv_series[-6]
        out["obv_change_5d"] = (
            (obv_series[-1] - prev_obv) / abs(prev_obv) if prev_obv != 0 else 0.0
        )
    else:
        out["obv_change_5d"] = None

    # ── Volume + price Z-scores ─────────────────────────────────
    if n >= 20:
        out["volume_z_20"] = _z_score(volumes[-20:], volumes[-1])
    else:
        out["volume_z_20"] = None
    if n >= 50:
        out["price_z_50"] = _z_score(closes[-50:], last)
    else:
        out["price_z_50"] = None

    # ── Market + macro context ──────────────────────────────────
    out["kse100_return_pct"] = context.kse100_return_pct if context else None
    out["sector_return_pct"] = context.sector_return_pct if context else None
    out["kibor_6m_pct"] = context.kibor_6m_pct if context else None
    out["pkr_usd_change_pct"] = context.pkr_usd_change_pct if context else None

    return out


# Stable feature ordering — the model interface and tests depend on this.
FEATURE_NAMES: tuple[str, ...] = (
    "log_return_1d",
    "log_return_5d",
    "log_return_10d",
    "log_return_20d",
    "momentum_10",
    "disparity_5",
    "disparity_10",
    "rsi_14",
    "stochastic_k",
    "stochastic_d",
    "williams_r_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "bollinger_pct_b",
    "atr_14_norm",
    "obv_change_5d",
    "volume_z_20",
    "price_z_50",
    "kse100_return_pct",
    "sector_return_pct",
    "kibor_6m_pct",
    "pkr_usd_change_pct",
)
