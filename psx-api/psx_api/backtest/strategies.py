"""
The five preset strategies the backtest UI ships with.

Each is a thin wrapper that takes a parameters dict and returns a
StrategyFn matching the engine's contract. Keep them tiny and explicit
— this is teaching code as much as it is signal-generation code.

  - sma_crossover:    50/200-day SMA "golden cross" / "death cross"
  - rsi_oversold:     buy <30, sell >70
  - macd_signal:      MACD line crosses above/below its signal line
  - bollinger_revert: buy at lower band, sell at middle band
  - buy_and_hold:     enter on first bar, never exit (benchmark)
"""

from __future__ import annotations

from typing import Callable

from psx_api.backtest.engine import Bar
from psx_api.indicators import compute


# Each entry: (key, label, default_params, factory)
_REGISTRY: dict[str, dict] = {}


def _register(key: str, label: str, default_params: dict, factory: Callable) -> None:
    _REGISTRY[key] = {"label": label, "default_params": default_params, "factory": factory}


def get_strategy(key: str, params: dict | None = None) -> Callable[[list[Bar], int], "int | tuple[int, str]"]:
    if key not in _REGISTRY:
        raise ValueError(f"Unknown strategy '{key}'. Valid: {sorted(_REGISTRY.keys())}")
    merged = {**_REGISTRY[key]["default_params"], **(params or {})}
    return _REGISTRY[key]["factory"](merged)


def list_strategies() -> list[dict]:
    return [
        {"key": k, "label": v["label"], "default_params": v["default_params"]}
        for k, v in _REGISTRY.items()
    ]


# ── Helpers ────────────────────────────────────────────────────────────


def _closes(bars: list[Bar]) -> list[float]:
    return [b.adjusted_close for b in bars]


# ── 1. SMA crossover ───────────────────────────────────────────────────


def _sma_crossover_factory(params: dict):
    fast = int(params["fast_period"])
    slow = int(params["slow_period"])

    def strategy(bars: list[Bar], i: int):
        closes = _closes(bars[: i + 1])
        if len(closes) < slow + 1:
            return 0
        fast_now = compute.sma(closes, fast)[-1]
        slow_now = compute.sma(closes, slow)[-1]
        fast_prev = compute.sma(closes[:-1], fast)[-1]
        slow_prev = compute.sma(closes[:-1], slow)[-1]
        if fast_now is None or slow_now is None or fast_prev is None or slow_prev is None:
            return 0
        if fast_now > slow_now:
            if fast_prev <= slow_prev:
                return 1, f"Golden cross: SMA-{fast} ({fast_now:.1f}) crossed above SMA-{slow} ({slow_now:.1f})"
            return 1, ""
        if fast_prev >= slow_prev:
            return 0, f"Death cross: SMA-{fast} ({fast_now:.1f}) crossed below SMA-{slow} ({slow_now:.1f})"
        return 0, ""

    return strategy


_register(
    "sma_crossover",
    "SMA Crossover (50/200)",
    {"fast_period": 50, "slow_period": 200},
    _sma_crossover_factory,
)


# ── 2. RSI oversold/overbought ─────────────────────────────────────────


def _rsi_oversold_factory(params: dict):
    period = int(params["period"])
    oversold = float(params["oversold"])
    overbought = float(params["overbought"])

    def strategy(bars: list[Bar], i: int):
        closes = _closes(bars[: i + 1])
        if len(closes) < period + 2:
            return 0
        rsi_now = compute.rsi(closes, period)[-1]
        if rsi_now is None:
            return 0
        if rsi_now < oversold:
            return 1, f"RSI {rsi_now:.1f} below {oversold:.0f} — oversold buy signal"
        if rsi_now > overbought:
            return 0, f"RSI {rsi_now:.1f} above {overbought:.0f} — overbought, exit"
        return None  # type: ignore[return-value]  # ambiguous → keep current state

    # The engine expects 1/0 only. Wrap to coerce "no opinion" into "hold current".
    state = {"long": False}

    def stateful(bars: list[Bar], i: int):
        decision = strategy(bars, i)
        if decision is None:
            return 1 if state["long"] else 0
        target = decision[0] if isinstance(decision, tuple) else decision
        state["long"] = target == 1
        return decision

    return stateful


_register(
    "rsi_oversold",
    "RSI Oversold/Overbought (30/70)",
    {"period": 14, "oversold": 30, "overbought": 70},
    _rsi_oversold_factory,
)


# ── 3. MACD signal cross ───────────────────────────────────────────────


def _macd_signal_factory(params: dict):
    fast = int(params["fast"])
    slow = int(params["slow"])
    signal_period = int(params["signal"])

    def strategy(bars: list[Bar], i: int):
        closes = _closes(bars[: i + 1])
        if len(closes) < slow + signal_period + 5:
            return 0
        d = compute.macd(closes, fast=fast, slow=slow, signal_period=signal_period)
        macd_now, sig_now = d["macd"][-1], d["signal"][-1]
        if macd_now is None or sig_now is None:
            return 0
        if macd_now > sig_now:
            return 1, f"MACD ({macd_now:.2f}) above signal ({sig_now:.2f}) — momentum bullish"
        return 0, f"MACD ({macd_now:.2f}) below signal ({sig_now:.2f}) — momentum bearish"

    return strategy


_register(
    "macd_signal",
    "MACD Signal-Line Cross",
    {"fast": 12, "slow": 26, "signal": 9},
    _macd_signal_factory,
)


# ── 4. Bollinger Band mean reversion ───────────────────────────────────


def _bollinger_revert_factory(params: dict):
    period = int(params["period"])
    num_std = float(params["num_std"])

    def strategy(bars: list[Bar], i: int):
        closes = _closes(bars[: i + 1])
        if len(closes) < period + 1:
            return 0
        d = compute.bollinger_bands(closes, period=period, num_std=num_std)
        upper, middle, lower = d["upper"][-1], d["middle"][-1], d["lower"][-1]
        if upper is None or middle is None or lower is None:
            return 0
        price = closes[-1]
        if price <= lower:
            return 1, f"Price ({price:.1f}) at/below lower band ({lower:.1f}) — mean-revert long"
        if price >= middle:
            return 0, f"Price ({price:.1f}) reverted to middle band ({middle:.1f}) — exit"
        return None  # type: ignore[return-value]

    state = {"long": False}

    def stateful(bars: list[Bar], i: int):
        decision = strategy(bars, i)
        if decision is None:
            return 1 if state["long"] else 0
        target = decision[0] if isinstance(decision, tuple) else decision
        state["long"] = target == 1
        return decision

    return stateful


_register(
    "bollinger_revert",
    "Bollinger Band Mean Reversion (20, 2σ)",
    {"period": 20, "num_std": 2.0},
    _bollinger_revert_factory,
)


# ── 5. Buy and hold (benchmark) ────────────────────────────────────────


def _buy_and_hold_factory(_params: dict):
    def strategy(bars: list[Bar], i: int):
        # Always want to be long. Engine will open on the next bar's open.
        if i == 0 or len(bars) < 2:
            return 0
        return 1, "Buy and hold benchmark"

    return strategy


_register(
    "buy_and_hold",
    "Buy and Hold (benchmark)",
    {},
    _buy_and_hold_factory,
)
