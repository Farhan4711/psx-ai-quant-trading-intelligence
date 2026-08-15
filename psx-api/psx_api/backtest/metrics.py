"""
Performance metrics from a BacktestRun.

All values are *annualised* where applicable, assuming 252 trading days
per year (standard equities convention; PSX runs ~250 days). Risk-free
rate is hard-coded to 0 for v1 — Phase 3 wires KIBOR in for an actual
Sharpe vs cash. Document the simplification rather than hide it.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from psx_api.backtest.engine import BacktestRun

_TRADING_DAYS = 252


@dataclass(frozen=True)
class BacktestMetrics:
    final_value_pkr: float
    total_return_pct: float
    cagr_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    num_trades: int
    win_rate_pct: float
    avg_winning_trade_pct: float
    avg_losing_trade_pct: float
    avg_holding_days: float
    total_commissions_pkr: float
    benchmark_return_pct: float  # buy-and-hold over the same period
    excess_return_pct: float  # strategy − benchmark


def compute_metrics(run: BacktestRun, *, benchmark_return_pct: float) -> BacktestMetrics:
    capital = run.initial_capital_pkr
    final = run.final_equity_pkr
    total_return = (final - capital) / capital * 100 if capital > 0 else 0.0

    # CAGR — uses calendar days for annualisation so short backtests stay honest
    if len(run.equity_curve) >= 2 and capital > 0:
        days = (run.equity_curve[-1].date - run.equity_curve[0].date).days
        years = max(days / 365.25, 1 / 365.25)
        cagr = ((final / capital) ** (1 / years) - 1) * 100 if final > 0 else -100.0
    else:
        cagr = 0.0

    # Sharpe from daily equity returns
    daily_returns: list[float] = []
    for prev, curr in zip(run.equity_curve, run.equity_curve[1:], strict=False):
        if prev.equity_pkr > 0:
            daily_returns.append((curr.equity_pkr - prev.equity_pkr) / prev.equity_pkr)
    if daily_returns:
        mean_r = sum(daily_returns) / len(daily_returns)
        var = sum((r - mean_r) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1)
        std = sqrt(var) if var > 0 else 0.0
        sharpe = (mean_r / std) * sqrt(_TRADING_DAYS) if std > 0 else 0.0
    else:
        sharpe = 0.0

    max_dd = max((p.drawdown_pct for p in run.equity_curve), default=0.0)

    # Trade stats
    trades = run.trades
    if trades:
        wins = [t for t in trades if t.net_pnl_pkr > 0]
        losses = [t for t in trades if t.net_pnl_pkr <= 0]
        win_rate = len(wins) / len(trades) * 100
        avg_win = sum(t.return_pct for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t.return_pct for t in losses) / len(losses) if losses else 0.0
        avg_hold = sum(t.holding_days for t in trades) / len(trades)
        total_commission = sum(t.commission_pkr for t in trades)
    else:
        win_rate = avg_win = avg_loss = avg_hold = total_commission = 0.0

    return BacktestMetrics(
        final_value_pkr=final,
        total_return_pct=total_return,
        cagr_pct=cagr,
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_dd,
        num_trades=len(trades),
        win_rate_pct=win_rate,
        avg_winning_trade_pct=avg_win,
        avg_losing_trade_pct=avg_loss,
        avg_holding_days=avg_hold,
        total_commissions_pkr=total_commission,
        benchmark_return_pct=benchmark_return_pct,
        excess_return_pct=total_return - benchmark_return_pct,
    )


def buy_and_hold_return_pct(run: BacktestRun) -> float:
    """
    What a simple all-in buy-and-hold over the same window would have
    returned (gross of fees, fair benchmark for relative comparisons).
    """
    if len(run.bars) < 2:
        return 0.0
    first = run.bars[0].adjusted_close
    last = run.bars[-1].adjusted_close
    if first <= 0:
        return 0.0
    return (last - first) / first * 100
