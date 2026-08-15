from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

StrategyKey = Literal[
    "sma_crossover",
    "rsi_oversold",
    "macd_signal",
    "bollinger_revert",
    "buy_and_hold",
]


class StrategyMeta(BaseModel):
    key: str
    label: str
    default_params: dict[str, Any]


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    strategy: StrategyKey
    start_date: date
    end_date: date
    initial_capital_pkr: Decimal = Field(default=Decimal("100000"), gt=0)
    commission_per_side_pct: float = Field(default=0.15, ge=0, le=5)
    parameters: dict[str, Any] = Field(default_factory=dict)


class TradeOut(BaseModel):
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    quantity: float
    commission_pkr: float
    gross_pnl_pkr: float
    net_pnl_pkr: float
    return_pct: float
    holding_days: int
    reason_open: str
    reason_close: str
    narration: str


class EquityPointOut(BaseModel):
    date: date
    equity_pkr: float
    drawdown_pct: float
    in_position: bool


class BacktestResult(BaseModel):
    symbol: str
    strategy: str
    start_date: date
    end_date: date
    initial_capital_pkr: float
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
    benchmark_return_pct: float
    excess_return_pct: float
    trades: list[TradeOut]
    equity_curve: list[EquityPointOut]
    lessons: list[str]
