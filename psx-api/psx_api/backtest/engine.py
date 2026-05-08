"""
Pure-Python backtest engine — no pandas, no vectorbt.

Daily-bar event loop walks OHLCV chronologically. Strategies emit a
target position (1 = long, 0 = flat) for each bar; the engine fills at
**next-day open** to avoid look-ahead bias, applies commission per side,
and tracks the resulting equity curve, trade ledger, and daily returns.

Why pure Python:
  - vectorbt is a 60+ MB transitive dep tree, overkill for daily bars
  - Retail use cases (5 yrs × 1 stock = ~1250 bars) run in <100 ms
  - The educational narration in Step 39 needs per-trade context that
    vector pipelines hide behind boolean masks; an explicit loop is
    easier to teach from

Look-ahead avoidance:
  - Indicators use only bar[0..i] when sizing the bar-i+1 fill
  - Commission applied symmetrically on entry + exit
  - Adjusted close used for indicator math (split/dividend stable)
  - Open price used for fills (matches how a market order at next open
    would actually execute)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable, Sequence


@dataclass(frozen=True)
class Bar:
    """One daily OHLCV bar. `adjusted_close` is what indicators see."""

    date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: float


@dataclass(frozen=True)
class Trade:
    """Closed round-trip — open + close fills, with computed economics."""

    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    quantity: float
    commission_pkr: float
    gross_pnl_pkr: float       # (exit - entry) * qty, ignores fees
    net_pnl_pkr: float         # after commissions
    return_pct: float          # net_pnl / (entry_price * qty)
    holding_days: int
    reason_open: str           # human-readable signal trigger
    reason_close: str


@dataclass
class EquityPoint:
    date: date
    equity_pkr: float
    drawdown_pct: float        # from running high-water mark
    in_position: bool


@dataclass
class BacktestRun:
    """Raw output of `run()`. Metrics + narration are layered on top."""

    bars: Sequence[Bar]
    equity_curve: list[EquityPoint]
    trades: list[Trade]
    initial_capital_pkr: float
    final_equity_pkr: float
    commission_per_side_pct: float


# ── Strategy contract ──────────────────────────────────────────────────

# A strategy receives the full bar history up to and including index `i`
# and returns 1 (want to be long going into the next bar) or 0 (want flat).
# It can also return a tuple `(target, reason)` where reason is the short
# human-readable trigger string ("RSI 28 < 30 → buy", "Golden cross", ...).
StrategyFn = Callable[[list[Bar], int], "int | tuple[int, str]"]


# ── Engine ─────────────────────────────────────────────────────────────


def run(
    bars: Sequence[Bar],
    *,
    strategy: StrategyFn,
    initial_capital_pkr: float,
    commission_per_side_pct: float = 0.15,  # default 0.15% retail rate
    warmup_bars: int = 200,                  # don't trade before SMA-200 has enough data
) -> BacktestRun:
    """
    Walk the bar history, emit fills at next-bar open, return everything
    needed to compute metrics and narration.

    Cash position only — no leverage, no shorts. Fully invested when long.
    """
    if not bars:
        raise ValueError("bars must be non-empty")
    if initial_capital_pkr <= 0:
        raise ValueError("initial_capital_pkr must be positive")

    bars_list = list(bars)
    cash = initial_capital_pkr
    quantity = 0.0
    entry: dict | None = None  # type: ignore[type-arg]
    trades: list[Trade] = []
    equity_curve: list[EquityPoint] = []
    high_water = initial_capital_pkr

    commission_rate = commission_per_side_pct / 100.0

    # Walk bars 0..n-1; signal at i drives fill at open of i+1.
    # The last bar can't trigger a fill (no next open) — we close any open
    # position at the last close as a forced exit so PnL is consistent.
    for i in range(len(bars_list)):
        bar = bars_list[i]

        # Sentence-by-sentence: compute current equity (mark-to-market),
        # update drawdown, then decide what to do at next open.
        current_equity = cash + quantity * bar.close
        if current_equity > high_water:
            high_water = current_equity
        drawdown = (
            ((high_water - current_equity) / high_water * 100)
            if high_water > 0
            else 0.0
        )
        equity_curve.append(
            EquityPoint(
                date=bar.date,
                equity_pkr=current_equity,
                drawdown_pct=drawdown,
                in_position=quantity > 0,
            )
        )

        if i < warmup_bars:
            continue

        # Strategy decision based on bars[0..i]
        if i + 1 >= len(bars_list):
            # Last bar — force-close any open position at this bar's close
            if quantity > 0 and entry is not None:
                fill_price = bar.close
                commission = fill_price * quantity * commission_rate
                proceeds = fill_price * quantity - commission
                cash += proceeds
                gross = (fill_price - entry["price"]) * quantity
                total_commission = entry["commission"] + commission
                net = gross - total_commission
                trades.append(
                    Trade(
                        entry_date=entry["date"],
                        entry_price=entry["price"],
                        exit_date=bar.date,
                        exit_price=fill_price,
                        quantity=quantity,
                        commission_pkr=total_commission,
                        gross_pnl_pkr=gross,
                        net_pnl_pkr=net,
                        return_pct=(net / (entry["price"] * quantity)) * 100
                        if entry["price"] > 0
                        else 0.0,
                        holding_days=(bar.date - entry["date"]).days,
                        reason_open=entry["reason"],
                        reason_close="End of backtest period",
                    )
                )
                quantity = 0.0
                entry = None
            continue

        decision = strategy(bars_list, i)
        if isinstance(decision, tuple):
            target, reason = decision
        else:
            target, reason = decision, ""

        next_bar = bars_list[i + 1]
        fill_price = next_bar.open

        if target == 1 and quantity == 0:
            # Open long at next open — buy as much as cash buys (after commission)
            target_qty = cash / (fill_price * (1 + commission_rate))
            if target_qty <= 0:
                continue
            commission = fill_price * target_qty * commission_rate
            cost = fill_price * target_qty + commission
            cash -= cost
            quantity = target_qty
            entry = {
                "date": next_bar.date,
                "price": fill_price,
                "commission": commission,
                "reason": reason or "Strategy signalled long",
            }

        elif target == 0 and quantity > 0 and entry is not None:
            commission = fill_price * quantity * commission_rate
            proceeds = fill_price * quantity - commission
            cash += proceeds
            gross = (fill_price - entry["price"]) * quantity
            total_commission = entry["commission"] + commission
            net = gross - total_commission
            trades.append(
                Trade(
                    entry_date=entry["date"],
                    entry_price=entry["price"],
                    exit_date=next_bar.date,
                    exit_price=fill_price,
                    quantity=quantity,
                    commission_pkr=total_commission,
                    gross_pnl_pkr=gross,
                    net_pnl_pkr=net,
                    return_pct=(net / (entry["price"] * quantity)) * 100
                    if entry["price"] > 0
                    else 0.0,
                    holding_days=(next_bar.date - entry["date"]).days,
                    reason_open=entry["reason"],
                    reason_close=reason or "Strategy signalled flat",
                )
            )
            quantity = 0.0
            entry = None

    final_equity = (
        equity_curve[-1].equity_pkr if equity_curve else initial_capital_pkr
    )
    return BacktestRun(
        bars=bars_list,
        equity_curve=equity_curve,
        trades=trades,
        initial_capital_pkr=initial_capital_pkr,
        final_equity_pkr=final_equity,
        commission_per_side_pct=commission_per_side_pct,
    )
