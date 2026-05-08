"""
Custom strategy parser — turns a JSON rule chain into a StrategyFn the
Phase 2B backtest engine can run.

Rule format (top-level):
{
  "entry": {"all_of": [Condition, Condition, ...]},
  "exit":  {"any_of": [Condition, Condition, ...]},
}

Condition shape:
{
  "left":     {"kind": "indicator", "name": "rsi", "period": 14}
              | {"kind": "indicator", "name": "sma", "period": 20}
              | {"kind": "price"}                 # current close
              | {"kind": "constant", "value": 30}
  "operator": "<" | "<=" | ">" | ">=" | "=="
  "right":    same shape as left
}

Plus a meta exit condition for time stops:
  {"kind": "holding_days_gt", "value": 30}

Whole thing is intentionally narrow. We *don't* support arbitrary math
expressions because (a) it's a security exposure (eval), and (b) most
real strategies fit cleanly into a list of indicator-comparator-value
clauses. When this becomes limiting we'll grow it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from psx_api.backtest.engine import Bar
from psx_api.indicators import compute


# ── Errors ──────────────────────────────────────────────────────────────


class InvalidStrategy(ValueError):
    """User-facing parsing/validation error — surfaced as 400."""


# ── Operand evaluation ──────────────────────────────────────────────────


def _eval_operand(operand: dict, bars: list[Bar], i: int) -> float | None:
    kind = operand.get("kind")
    closes = [b.close for b in bars[: i + 1]]

    if kind == "constant":
        try:
            return float(operand["value"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidStrategy(f"Bad constant: {operand}") from exc

    if kind == "price":
        return closes[-1] if closes else None

    if kind == "indicator":
        name = operand.get("name", "").lower()
        period = int(operand.get("period", 14))
        if name == "rsi":
            return compute.rsi(closes, period)[-1]
        if name == "sma":
            return compute.sma(closes, period)[-1]
        if name == "ema":
            return compute.ema(closes, period)[-1]
        if name == "macd_histogram":
            d = compute.macd(closes)
            return d["histogram"][-1]
        if name == "stochastic_k":
            highs = [b.high for b in bars[: i + 1]]
            lows = [b.low for b in bars[: i + 1]]
            return compute.stochastic(highs, lows, closes, k_period=period)["k"][-1]
        if name == "atr":
            highs = [b.high for b in bars[: i + 1]]
            lows = [b.low for b in bars[: i + 1]]
            return compute.atr(highs, lows, closes, period=period)[-1]
        if name == "volume":
            return bars[i].volume if i < len(bars) else None
        raise InvalidStrategy(f"Unknown indicator '{name}'")

    raise InvalidStrategy(f"Unknown operand kind '{kind}'")


_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


def _eval_condition(cond: dict, bars: list[Bar], i: int) -> bool:
    # Special case: holding_days_gt — only the engine wrapper knows
    # how many days a position has been open. Surfaced as a separate
    # exit clause; if seen here, it's the caller's responsibility.
    if cond.get("kind") == "holding_days_gt":
        return False

    op = cond.get("operator")
    if op not in _OPS:
        raise InvalidStrategy(f"Unknown operator '{op}'")
    left = _eval_operand(cond.get("left", {}), bars, i)
    right = _eval_operand(cond.get("right", {}), bars, i)
    if left is None or right is None:
        return False
    return _OPS[op](left, right)


def _eval_group(group: dict, bars: list[Bar], i: int) -> bool:
    if "all_of" in group:
        return all(_eval_condition(c, bars, i) for c in group["all_of"])
    if "any_of" in group:
        return any(_eval_condition(c, bars, i) for c in group["any_of"])
    # Single condition shorthand
    if "operator" in group or "kind" in group:
        return _eval_condition(group, bars, i)
    raise InvalidStrategy(f"Group must have all_of or any_of: {group}")


# ── Public API ──────────────────────────────────────────────────────────


def validate(rules: dict) -> None:
    """Raises InvalidStrategy if `rules` is malformed."""
    if not isinstance(rules, dict):
        raise InvalidStrategy("Rules must be an object.")
    if "entry" not in rules:
        raise InvalidStrategy("Rules must include an `entry` clause.")
    # exit is optional; if missing we trade buy-and-hold semantics
    # Walk and try to evaluate against a tiny synthetic dataset to surface
    # parser errors early.
    synthetic = [
        Bar(date=__import__("datetime").date(2024, 1, i + 1), open=100.0, high=101.0, low=99.0, close=100.0, adjusted_close=100.0, volume=1000.0)
        for i in range(20)
    ]
    try:
        _eval_group(rules["entry"], synthetic, len(synthetic) - 1)
    except InvalidStrategy:
        raise
    except Exception as exc:
        raise InvalidStrategy(f"Entry rule failed validation: {exc}") from exc

    if "exit" in rules:
        try:
            # Strip holding_days_gt for synthetic eval
            exit_clean = _strip_meta(rules["exit"])
            if exit_clean:
                _eval_group(exit_clean, synthetic, len(synthetic) - 1)
        except InvalidStrategy:
            raise
        except Exception as exc:
            raise InvalidStrategy(f"Exit rule failed validation: {exc}") from exc


def _strip_meta(group: dict) -> dict | None:
    """Drop holding_days_gt clauses for parser-only validation."""
    if "all_of" in group or "any_of" in group:
        key = "all_of" if "all_of" in group else "any_of"
        kept = [c for c in group[key] if c.get("kind") != "holding_days_gt"]
        if not kept:
            return None
        return {key: kept}
    if group.get("kind") == "holding_days_gt":
        return None
    return group


def build_strategy(
    rules: dict,
) -> Callable[[list[Bar], int], "int | tuple[int, str]"]:
    """
    Returns a StrategyFn matching the engine contract. Captures internal
    state (entry index) so the holding_days_gt exit clause works.
    """
    validate(rules)
    state = {"long": False, "entry_index": -1}
    holding_days_max = _holding_days_max(rules.get("exit"))

    def strategy(bars: list[Bar], i: int):
        if not state["long"]:
            if _eval_group(rules["entry"], bars, i):
                state["long"] = True
                state["entry_index"] = i + 1  # fill happens at i+1
                return 1, "Custom rules: entry conditions met"
            return 0
        # Currently long — check exits
        if "exit" in rules:
            exit_clean = _strip_meta(rules["exit"])
            if exit_clean and _eval_group(exit_clean, bars, i):
                state["long"] = False
                return 0, "Custom rules: exit conditions met"
        if (
            holding_days_max is not None
            and state["entry_index"] >= 0
            and (i - state["entry_index"]) >= holding_days_max
        ):
            state["long"] = False
            return 0, f"Custom rules: max holding period {holding_days_max} reached"
        return 1

    return strategy


def _holding_days_max(exit_group: dict | None) -> int | None:
    if not exit_group:
        return None
    nodes: list[dict] = []
    if "all_of" in exit_group:
        nodes = exit_group["all_of"]
    elif "any_of" in exit_group:
        nodes = exit_group["any_of"]
    elif exit_group.get("kind") == "holding_days_gt":
        try:
            return int(exit_group["value"])
        except (KeyError, TypeError, ValueError):
            return None
    for n in nodes:
        if n.get("kind") == "holding_days_gt":
            try:
                return int(n["value"])
            except (KeyError, TypeError, ValueError):
                continue
    return None
