"""
Plain-English interpretation of indicator readings for the user-facing
panel. Each helper returns:

  signal   : "bullish" | "bearish" | "neutral"  (drives the traffic light)
  summary  : 2-3 sentence explanation tied to the actual value
  explainer: long-form "What is X?" markdown the UI shows on demand

This is opinionated content — the goal is plain language, not technical
jargon. We err on the side of cautionary phrasing and never frame a
single indicator as a buy/sell instruction.
"""

from __future__ import annotations

from typing import Literal

Signal = Literal["bullish", "bearish", "neutral"]


def _pkg(signal: Signal, summary: str, explainer: str, value: dict) -> dict:
    return {"signal": signal, "summary": summary, "explainer": explainer, "value": value}


def interpret_rsi(value: float | None) -> dict:
    explainer = (
        "**RSI (Relative Strength Index)** measures how fast a stock has been "
        "rising or falling on a 0–100 scale. Above 70 is traditionally called "
        "*overbought* — recent gains have been sharp and a pullback is more "
        "likely. Below 30 is *oversold* — a bounce is more likely. RSI is a "
        "momentum indicator, not a timing tool. Stocks can stay overbought or "
        "oversold for a long time, especially during strong trends."
    )
    if value is None:
        return _pkg("neutral", "Not enough history to compute RSI yet.", explainer, {"rsi": None})
    if value >= 70:
        return _pkg(
            "bearish",
            f"RSI is {value:.1f}. Above 70 typically suggests the stock is "
            "overbought and may pull back. This is a cautionary signal, not a sell order.",
            explainer,
            {"rsi": value},
        )
    if value <= 30:
        return _pkg(
            "bullish",
            f"RSI is {value:.1f}. Below 30 typically suggests the stock is "
            "oversold and may bounce. This is a cautionary signal, not a buy order.",
            explainer,
            {"rsi": value},
        )
    return _pkg(
        "neutral",
        f"RSI is {value:.1f} — a neutral reading. The stock is neither overbought nor oversold.",
        explainer,
        {"rsi": value},
    )


def interpret_macd(macd: float | None, signal_v: float | None, hist: float | None) -> dict:
    explainer = (
        "**MACD (Moving Average Convergence Divergence)** plots the difference "
        "between a fast and slow exponential moving average, plus a signal line "
        "that's an EMA of that difference. When the MACD crosses above its "
        "signal line, momentum is turning up. When it crosses below, momentum "
        "is turning down. The histogram is the gap between the two — bigger "
        "bars mean stronger momentum."
    )
    if macd is None or signal_v is None or hist is None:
        return _pkg(
            "neutral",
            "Not enough history to compute MACD yet.",
            explainer,
            {"macd": macd, "signal": signal_v, "histogram": hist},
        )
    if hist > 0 and macd > 0:
        return _pkg(
            "bullish",
            f"MACD ({macd:.2f}) is above its signal line ({signal_v:.2f}) — "
            "short-term momentum is positive.",
            explainer,
            {"macd": macd, "signal": signal_v, "histogram": hist},
        )
    if hist < 0 and macd < 0:
        return _pkg(
            "bearish",
            f"MACD ({macd:.2f}) is below its signal line ({signal_v:.2f}) — "
            "short-term momentum is negative.",
            explainer,
            {"macd": macd, "signal": signal_v, "histogram": hist},
        )
    return _pkg(
        "neutral",
        f"MACD ({macd:.2f}) and signal ({signal_v:.2f}) are crossing — momentum is shifting.",
        explainer,
        {"macd": macd, "signal": signal_v, "histogram": hist},
    )


def interpret_sma(close: float | None, sma_value: float | None, period: int) -> dict:
    explainer = (
        f"**SMA-{period} (Simple Moving Average)** is the average closing price "
        f"over the last {period} days. It smooths out daily noise and shows "
        "the underlying trend. Price above SMA = uptrend, price below = "
        "downtrend. The 50-day and 200-day SMAs are the two most-watched "
        "trend lines on the planet."
    )
    if close is None or sma_value is None:
        return _pkg(
            "neutral",
            f"Not enough history to compute SMA-{period}.",
            explainer,
            {"sma": sma_value, "close": close},
        )
    pct = (close - sma_value) / sma_value * 100
    if close > sma_value:
        return _pkg(
            "bullish",
            f"Price ({close:.2f}) is {pct:.1f}% above its {period}-day average "
            f"({sma_value:.2f}) — the trend is up.",
            explainer,
            {"sma": sma_value, "close": close, "delta_pct": pct},
        )
    return _pkg(
        "bearish",
        f"Price ({close:.2f}) is {abs(pct):.1f}% below its {period}-day average "
        f"({sma_value:.2f}) — the trend is down.",
        explainer,
        {"sma": sma_value, "close": close, "delta_pct": pct},
    )


def interpret_ema(close: float | None, ema_value: float | None, period: int) -> dict:
    base = interpret_sma(close, ema_value, period)
    base["explainer"] = (
        f"**EMA-{period} (Exponential Moving Average)** is like SMA but weights "
        "recent prices more heavily, so it reacts faster to changes. Traders "
        "favor EMA over SMA on short timeframes when they want to see "
        "momentum shifts sooner."
    )
    return base


def interpret_bollinger(
    close: float | None, upper: float | None, middle: float | None, lower: float | None
) -> dict:
    explainer = (
        "**Bollinger Bands** wrap a 20-day moving average with bands two "
        "standard deviations above and below. Most price action stays inside "
        "the bands. Price riding the upper band = strong uptrend (or potential "
        "exhaustion). Price riding the lower band = strong downtrend (or "
        "potential bottom). Width tells you about volatility — narrow bands "
        "often precede big moves."
    )
    if any(v is None for v in (close, upper, middle, lower)):
        return _pkg(
            "neutral",
            "Not enough history to compute Bollinger Bands.",
            explainer,
            {"upper": upper, "middle": middle, "lower": lower, "close": close},
        )
    assert close is not None and upper is not None and middle is not None and lower is not None
    if close >= upper:
        return _pkg(
            "bearish",
            f"Price ({close:.2f}) is at or above the upper band ({upper:.2f}) — "
            "the stock is statistically extended; a pullback or sideways move is more likely.",
            explainer,
            {"upper": upper, "middle": middle, "lower": lower, "close": close},
        )
    if close <= lower:
        return _pkg(
            "bullish",
            f"Price ({close:.2f}) is at or below the lower band ({lower:.2f}) — "
            "the stock is statistically stretched; a bounce or sideways move is more likely.",
            explainer,
            {"upper": upper, "middle": middle, "lower": lower, "close": close},
        )
    return _pkg(
        "neutral",
        f"Price ({close:.2f}) is inside the bands ({lower:.2f}–{upper:.2f}). Normal range.",
        explainer,
        {"upper": upper, "middle": middle, "lower": lower, "close": close},
    )


def interpret_stochastic(k: float | None, d: float | None) -> dict:
    explainer = (
        "**Stochastic Oscillator** measures where today's close sits within "
        "the recent high–low range, on a 0–100 scale. Above 80 is overbought, "
        "below 20 is oversold. Like RSI, it's momentum, not timing — strong "
        "trends can pin %K at the extremes."
    )
    if k is None or d is None:
        return _pkg("neutral", "Not enough history to compute Stochastic.", explainer, {"k": k, "d": d})
    if k > 80:
        return _pkg(
            "bearish",
            f"Stochastic %K is {k:.1f}. Above 80 = overbought territory.",
            explainer,
            {"k": k, "d": d},
        )
    if k < 20:
        return _pkg(
            "bullish",
            f"Stochastic %K is {k:.1f}. Below 20 = oversold territory.",
            explainer,
            {"k": k, "d": d},
        )
    return _pkg(
        "neutral",
        f"Stochastic %K is {k:.1f} — neutral.",
        explainer,
        {"k": k, "d": d},
    )


def interpret_obv(latest: float | None, week_ago: float | None) -> dict:
    explainer = (
        "**OBV (On-Balance Volume)** adds up volume on up-days and subtracts "
        "it on down-days. Rising OBV = volume is supporting the uptrend. "
        "Falling OBV during a price uptrend = a divergence worth watching, "
        "since the rally may not have buyer conviction behind it."
    )
    if latest is None or week_ago is None:
        return _pkg(
            "neutral",
            "Not enough history to read OBV trend.",
            explainer,
            {"obv": latest, "obv_week_ago": week_ago},
        )
    delta = latest - week_ago
    if delta > 0:
        return _pkg(
            "bullish",
            "OBV is rising over the past week — buyers have been more active than sellers.",
            explainer,
            {"obv": latest, "obv_week_ago": week_ago, "delta": delta},
        )
    if delta < 0:
        return _pkg(
            "bearish",
            "OBV is falling over the past week — sellers have been more active than buyers.",
            explainer,
            {"obv": latest, "obv_week_ago": week_ago, "delta": delta},
        )
    return _pkg(
        "neutral",
        "OBV is flat — buying and selling pressure are balanced.",
        explainer,
        {"obv": latest, "obv_week_ago": week_ago, "delta": delta},
    )


def interpret_atr(atr_value: float | None, close: float | None) -> dict:
    explainer = (
        "**ATR (Average True Range)** measures average daily volatility in PKR. "
        "It's not directional — it just tells you how much the stock typically "
        "moves in a day. Useful for sizing positions: divide your risk budget "
        "by ATR to figure out a sensible stop-loss distance."
    )
    if atr_value is None or close is None:
        return _pkg("neutral", "Not enough history to compute ATR.", explainer, {"atr": atr_value})
    pct = atr_value / close * 100
    return _pkg(
        "neutral",
        f"Average daily range ≈ PKR {atr_value:.2f} ({pct:.1f}% of current price). "
        "Use this to size stop-losses.",
        explainer,
        {"atr": atr_value, "atr_pct_of_price": pct},
    )
