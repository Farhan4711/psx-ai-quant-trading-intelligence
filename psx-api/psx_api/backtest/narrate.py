"""
Plain-English narration for backtests.

Two outputs:

  - `narrate_trade(trade, symbol)` → one paragraph per trade explaining
    what triggered the entry/exit, position size, fees, and net P&L.
    This is the teaching tool — turns a trade list from data into a story.

  - `lessons(metrics)` → 1–4 short bullet observations the UI shows under
    the equity chart. Heuristics, not advice. Always frames the strategy
    against the buy-and-hold benchmark so users see the bar a passive
    investor sets.
"""

from __future__ import annotations

from psx_api.backtest.engine import Trade
from psx_api.backtest.metrics import BacktestMetrics


def _pkr(amount: float) -> str:
    """Format a PKR amount with thousands separators."""
    if amount < 0:
        return f"-PKR {abs(amount):,.0f}"
    return f"PKR {amount:,.0f}"


def narrate_trade(trade: Trade, symbol: str) -> str:
    pnl_word = "profit" if trade.net_pnl_pkr >= 0 else "loss"
    pnl_sign = "+" if trade.net_pnl_pkr >= 0 else ""
    return (
        f"On {trade.entry_date.isoformat()}, the strategy bought "
        f"{trade.quantity:.0f} shares of {symbol} at PKR {trade.entry_price:.2f} "
        f"({trade.reason_open}). The position was held for "
        f"{trade.holding_days} day{'s' if trade.holding_days != 1 else ''}. "
        f"On {trade.exit_date.isoformat()}, the strategy sold at "
        f"PKR {trade.exit_price:.2f} ({trade.reason_close}) for a gross {pnl_word} "
        f"of {_pkr(trade.gross_pnl_pkr)}, "
        f"reduced to {_pkr(trade.net_pnl_pkr)} after "
        f"{_pkr(trade.commission_pkr)} in commissions "
        f"({pnl_sign}{trade.return_pct:.2f}%)."
    )


def lessons(metrics: BacktestMetrics, *, strategy_label: str) -> list[str]:
    out: list[str] = []

    # 1. Did it beat buy-and-hold?
    if metrics.num_trades == 0:
        out.append(
            "The strategy never triggered a trade in this window. The signals "
            "either weren't met or the warm-up period covered the whole range."
        )
        return out

    if metrics.excess_return_pct < -2:
        out.append(
            f"Buy-and-hold beat **{strategy_label}** by "
            f"{abs(metrics.excess_return_pct):.1f}%. Active strategies need to "
            "overcome both fees AND the high bar of just holding good companies "
            "— most of them don't, on most stocks."
        )
    elif metrics.excess_return_pct > 2:
        out.append(
            f"**{strategy_label}** beat buy-and-hold by "
            f"{metrics.excess_return_pct:.1f}% over this period. Be careful: a "
            "single backtest is not proof a strategy 'works' — the market regime "
            "during this window may not repeat."
        )
    else:
        out.append(
            "Strategy and buy-and-hold finished within 2% of each other. After "
            "fees and effort, that's a wash — passive investing was the easier "
            "trade here."
        )

    # 2. Risk
    if metrics.max_drawdown_pct > 30:
        out.append(
            f"Peak-to-trough drawdown was **{metrics.max_drawdown_pct:.1f}%**. "
            "Could you actually have held through that without panicking? "
            "Real-life behaviour is the silent killer of backtest results."
        )

    # 3. Win rate context
    if metrics.num_trades >= 5:
        if metrics.win_rate_pct < 40:
            out.append(
                f"Win rate was **{metrics.win_rate_pct:.0f}%**. Most active "
                "strategies have low win rates and survive only because their "
                "few wins are much bigger than their many losses. Look at "
                "average winning vs losing trade size to check that pattern."
            )
        elif metrics.win_rate_pct > 70:
            out.append(
                f"Win rate was **{metrics.win_rate_pct:.0f}%**. That's high — "
                "but if average wins are smaller than average losses, the "
                "expectation can still be negative. Check the trade sizes."
            )

    # 4. Sharpe quality
    if metrics.sharpe_ratio > 1.5:
        out.append(
            f"Sharpe ratio of {metrics.sharpe_ratio:.2f} on this window is "
            "high — verify it holds out-of-sample before trusting it."
        )
    elif metrics.sharpe_ratio < 0:
        out.append(
            f"Sharpe ratio is negative ({metrics.sharpe_ratio:.2f}) — the "
            "strategy returned less per unit of risk than just holding cash."
        )

    return out
