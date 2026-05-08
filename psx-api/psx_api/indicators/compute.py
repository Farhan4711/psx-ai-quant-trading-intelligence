"""
Pure-Python technical indicator implementations.

We deliberately avoid pandas-ta / TA-Lib here — the math for the v1 set is
straightforward and a focused module with zero heavy deps is easier to
test, deploy, and reason about. If we later need the full 130+ indicator
library we can swap this out behind the IndicatorService interface.

All functions take simple lists/sequences of `float` (or `Decimal`) and
return lists aligned to the input length, with leading `None`s for
warm-up periods. Callers that want pandas-style Series can wrap.

Inputs:
  closes: chronological list of close prices (oldest → newest)
  highs / lows / volumes: same shape, where applicable

Outputs:
  list[float | None] of the same length as input, or a dict for multi-line
  indicators (MACD, BBands, Stochastic).
"""

from __future__ import annotations

from typing import Sequence


Number = float
Series = list[float | None]


# ── helpers ─────────────────────────────────────────────────────────────


def _to_floats(xs: Sequence[float]) -> list[float]:
    return [float(x) for x in xs]


# ── moving averages ─────────────────────────────────────────────────────


def sma(closes: Sequence[float], period: int) -> Series:
    if period <= 0:
        raise ValueError("period must be positive")
    xs = _to_floats(closes)
    out: Series = [None] * len(xs)
    if len(xs) < period:
        return out
    running = sum(xs[:period])
    out[period - 1] = running / period
    for i in range(period, len(xs)):
        running += xs[i] - xs[i - period]
        out[i] = running / period
    return out


def ema(closes: Sequence[float], period: int) -> Series:
    if period <= 0:
        raise ValueError("period must be positive")
    xs = _to_floats(closes)
    out: Series = [None] * len(xs)
    if len(xs) < period:
        return out
    # Seed with SMA of first `period` values
    seed = sum(xs[:period]) / period
    out[period - 1] = seed
    k = 2 / (period + 1)
    prev = seed
    for i in range(period, len(xs)):
        prev = xs[i] * k + prev * (1 - k)
        out[i] = prev
    return out


# ── momentum ────────────────────────────────────────────────────────────


def rsi(closes: Sequence[float], period: int = 14) -> Series:
    """Wilder's RSI."""
    if period <= 0:
        raise ValueError("period must be positive")
    xs = _to_floats(closes)
    out: Series = [None] * len(xs)
    if len(xs) <= period:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = xs[i] - xs[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)

    for i in range(period + 1, len(xs)):
        delta = xs[i] - xs[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def macd(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> dict[str, Series]:
    fast_line = ema(closes, fast)
    slow_line = ema(closes, slow)
    macd_line: Series = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(fast_line, slow_line)
    ]
    # Signal line = EMA of MACD line, computed only on the populated tail
    populated_idx = next(
        (i for i, v in enumerate(macd_line) if v is not None), len(macd_line)
    )
    populated = [v for v in macd_line[populated_idx:] if v is not None]
    sig_tail = ema(populated, signal_period) if populated else []
    signal_line: Series = [None] * len(closes)
    for offset, v in enumerate(sig_tail):
        signal_line[populated_idx + offset] = v
    histogram: Series = [
        (m - s) if (m is not None and s is not None) else None
        for m, s in zip(macd_line, signal_line)
    ]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def stochastic(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    k_period: int = 14,
    d_period: int = 3,
) -> dict[str, Series]:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs/lows/closes must be same length")
    n = len(closes)
    k_line: Series = [None] * n
    for i in range(k_period - 1, n):
        window_high = max(highs[i - k_period + 1 : i + 1])
        window_low = min(lows[i - k_period + 1 : i + 1])
        denom = window_high - window_low
        k_line[i] = 100 * (closes[i] - window_low) / denom if denom != 0 else 50.0
    # %D = SMA of %K
    populated_idx = next((i for i, v in enumerate(k_line) if v is not None), n)
    populated = [v for v in k_line[populated_idx:] if v is not None]
    d_tail = sma(populated, d_period) if populated else []
    d_line: Series = [None] * n
    for offset, v in enumerate(d_tail):
        d_line[populated_idx + offset] = v
    return {"k": k_line, "d": d_line}


# ── volatility ──────────────────────────────────────────────────────────


def bollinger_bands(
    closes: Sequence[float], period: int = 20, num_std: float = 2.0
) -> dict[str, Series]:
    xs = _to_floats(closes)
    middle = sma(xs, period)
    n = len(xs)
    upper: Series = [None] * n
    lower: Series = [None] * n
    for i in range(period - 1, n):
        window = xs[i - period + 1 : i + 1]
        mean = middle[i]
        if mean is None:
            continue
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance**0.5
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std
    return {"upper": upper, "middle": middle, "lower": lower}


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> Series:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs/lows/closes must be same length")
    n = len(closes)
    out: Series = [None] * n
    if n < period + 1:
        return out
    trs: list[float] = []
    for i in range(1, n):
        h, l, prev_c = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    # Wilder's smoothing
    first_atr = sum(trs[:period]) / period
    out[period] = first_atr
    prev = first_atr
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + trs[i - 1]) / period
        out[i] = prev
    return out


# ── volume ──────────────────────────────────────────────────────────────


def obv(closes: Sequence[float], volumes: Sequence[float]) -> Series:
    if len(closes) != len(volumes):
        raise ValueError("closes/volumes must be same length")
    n = len(closes)
    out: Series = [None] * n
    if n == 0:
        return out
    running = 0.0
    out[0] = 0.0
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            running += volumes[i]
        elif closes[i] < closes[i - 1]:
            running -= volumes[i]
        out[i] = running
    return out
