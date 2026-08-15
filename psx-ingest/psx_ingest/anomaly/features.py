"""
Anomaly feature extraction.

Mirrors the field order in `psx_api.alerts.pump_dump.AnomalyFeatures`
so the model trained here can be scored against features the
production detector builds.

Six features per bar (in stable order):
    close, volume, vol_spike, price_change_pct, intraday_range_pct, gap_pct
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

FEATURE_ORDER: tuple[str, ...] = (
    "close",
    "volume",
    "vol_spike",
    "price_change_pct",
    "intraday_range_pct",
    "gap_pct",
)


@dataclass(frozen=True, slots=True)
class Bar:
    open: float
    high: float
    low: float
    close: float
    volume: float


def vol_ma(values: Sequence[float], window: int = 20) -> list[float]:
    """Trailing simple moving average. First (window-1) entries are
    None so callers can align with bar indices without re-indexing."""
    out: list[float] = []
    rolling = 0.0
    for i, v in enumerate(values):
        rolling += v
        if i >= window:
            rolling -= values[i - window]
        if i + 1 >= window:
            out.append(rolling / window)
        else:
            out.append(0.0)
    return out


def features_for_bars(bars: Sequence[Bar]) -> list[list[float]]:
    """
    Build a (N x 6) feature matrix from an ordered list of bars
    (oldest → newest). The first 20 rows have `vol_spike=0` because
    the 20-day average isn't defined yet — the trainer drops them.
    """
    if not bars:
        return []
    volumes = [b.volume for b in bars]
    vol_ma_20 = vol_ma(volumes, 20)

    matrix: list[list[float]] = []
    for i, b in enumerate(bars):
        prev_close = bars[i - 1].close if i > 0 else b.open
        vol_spike = b.volume / vol_ma_20[i] if vol_ma_20[i] > 0 else 0.0
        price_change_pct = (b.close - b.open) / b.open * 100 if b.open > 0 else 0.0
        intraday_range_pct = (b.high - b.low) / b.open * 100 if b.open > 0 else 0.0
        gap_pct = (b.open - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
        matrix.append(
            [
                b.close,
                b.volume,
                vol_spike,
                price_change_pct,
                intraday_range_pct,
                gap_pct,
            ]
        )
    return matrix
