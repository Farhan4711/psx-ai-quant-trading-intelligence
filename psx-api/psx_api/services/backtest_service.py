"""
Backtest orchestration: load OHLCV from DB → run engine → compute metrics
→ render narration → assemble the response payload.

Synchronous. Daily-bar backtests on a single PSX symbol over 5 years are
~1250 bars and finish in well under 200 ms — no Celery needed at this
volume. We'll move to a job queue when bulk multi-stock optimisation
lands in Phase 3.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.backtest import metrics, narrate
from psx_api.backtest.engine import Bar, run
from psx_api.backtest.strategies import get_strategy
from psx_api.models.ohlcv import OhlcvDaily
from psx_api.models.securities import Security
from psx_api.schemas.backtest import (
    BacktestRequest,
    BacktestResult,
    EquityPointOut,
    TradeOut,
)


class BacktestError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class BacktestService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def run(self, req: BacktestRequest) -> BacktestResult:
        symbol = req.symbol.upper().strip()
        bars = await self._load_bars(symbol, req.start_date, req.end_date)
        if len(bars) < 30:
            raise BacktestError(
                f"Not enough OHLCV history for {symbol} between "
                f"{req.start_date} and {req.end_date} (got {len(bars)} bars). "
                "Pick a longer range or a more liquid symbol.",
                status_code=400,
            )

        strategy = get_strategy(req.strategy, req.parameters)
        # Cap warmup at half the bar count so short windows still run
        warmup = min(200, len(bars) // 2)
        bt = run(
            bars,
            strategy=strategy,
            initial_capital_pkr=float(req.initial_capital_pkr),
            commission_per_side_pct=req.commission_per_side_pct,
            warmup_bars=warmup,
        )

        benchmark_pct = metrics.buy_and_hold_return_pct(bt)
        m = metrics.compute_metrics(bt, benchmark_return_pct=benchmark_pct)

        from psx_api.backtest.strategies import list_strategies

        label = next(
            (s["label"] for s in list_strategies() if s["key"] == req.strategy),
            req.strategy,
        )

        return BacktestResult(
            symbol=symbol,
            strategy=req.strategy,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital_pkr=bt.initial_capital_pkr,
            final_value_pkr=m.final_value_pkr,
            total_return_pct=m.total_return_pct,
            cagr_pct=m.cagr_pct,
            sharpe_ratio=m.sharpe_ratio,
            max_drawdown_pct=m.max_drawdown_pct,
            num_trades=m.num_trades,
            win_rate_pct=m.win_rate_pct,
            avg_winning_trade_pct=m.avg_winning_trade_pct,
            avg_losing_trade_pct=m.avg_losing_trade_pct,
            avg_holding_days=m.avg_holding_days,
            total_commissions_pkr=m.total_commissions_pkr,
            benchmark_return_pct=m.benchmark_return_pct,
            excess_return_pct=m.excess_return_pct,
            trades=[
                TradeOut(
                    entry_date=t.entry_date,
                    entry_price=t.entry_price,
                    exit_date=t.exit_date,
                    exit_price=t.exit_price,
                    quantity=t.quantity,
                    commission_pkr=t.commission_pkr,
                    gross_pnl_pkr=t.gross_pnl_pkr,
                    net_pnl_pkr=t.net_pnl_pkr,
                    return_pct=t.return_pct,
                    holding_days=t.holding_days,
                    reason_open=t.reason_open,
                    reason_close=t.reason_close,
                    narration=narrate.narrate_trade(t, symbol),
                )
                for t in bt.trades
            ],
            equity_curve=[
                EquityPointOut(
                    date=p.date,
                    equity_pkr=p.equity_pkr,
                    drawdown_pct=p.drawdown_pct,
                    in_position=p.in_position,
                )
                for p in bt.equity_curve
            ],
            lessons=narrate.lessons(m, strategy_label=label),
        )

    # ------------------------------------------------------------------

    async def _load_bars(self, symbol: str, start: date, end: date) -> list[Bar]:
        # Make sure the symbol exists; surface a clean 404 otherwise.
        sec = (
            await self._db.execute(select(Security).where(Security.symbol == symbol))
        ).scalar_one_or_none()
        if not sec:
            raise BacktestError(f"Unknown symbol '{symbol}'.", status_code=404)

        rows = (
            await self._db.execute(
                select(
                    OhlcvDaily.date,
                    OhlcvDaily.open,
                    OhlcvDaily.high,
                    OhlcvDaily.low,
                    OhlcvDaily.close,
                    OhlcvDaily.adjusted_close,
                    OhlcvDaily.volume,
                )
                .where(
                    OhlcvDaily.symbol == symbol,
                    OhlcvDaily.date >= start,
                    OhlcvDaily.date <= end,
                )
                .order_by(OhlcvDaily.date)
            )
        ).all()
        bars: list[Bar] = []
        for d, o, h, low, c, adj, v in rows:
            if any(x is None for x in (o, h, low, c)):
                continue
            bars.append(
                Bar(
                    date=d,
                    open=float(o),
                    high=float(h),
                    low=float(low),
                    close=float(c),
                    adjusted_close=float(adj if adj is not None else c),
                    volume=float(v or 0),
                )
            )
        return bars
