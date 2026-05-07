from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TransactionTypeLiteral = Literal["buy", "sell", "dividend", "bonus", "rights"]


# ── Portfolios ─────────────────────────────────────────────────────────


class PortfolioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    base_currency: str = Field(default="PKR", min_length=3, max_length=3)
    is_default: bool = False


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_default: bool | None = None


class PortfolioResponse(PortfolioBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime


# ── Transactions ───────────────────────────────────────────────────────


class TransactionBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    transaction_type: TransactionTypeLiteral
    transaction_date: date
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    price_per_share: Decimal = Field(..., ge=0, decimal_places=4)
    brokerage_pkr: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)
    fed_pkr: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)
    cvt_pkr: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)
    cgt_pkr: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)
    notes: str | None = None

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.upper().strip()


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    portfolio_id: str
    created_at: datetime


# ── Holdings ───────────────────────────────────────────────────────────


class HoldingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    portfolio_id: str
    symbol: str
    quantity: Decimal
    avg_cost_pkr: Decimal
    total_invested_pkr: Decimal
    realized_pnl_pkr: Decimal
    total_dividends_received_pkr: Decimal
    updated_at: datetime


class HoldingWithMarket(HoldingResponse):
    """Holding enriched with latest market price for the dashboard view."""

    last_close: Decimal | None = None
    last_close_date: date | None = None
    market_value_pkr: Decimal | None = None
    unrealized_pnl_pkr: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None


class PortfolioSummary(BaseModel):
    """High-level rollup for the dashboard."""

    portfolio_id: str
    total_invested_pkr: Decimal
    current_value_pkr: Decimal
    unrealized_pnl_pkr: Decimal
    unrealized_pnl_pct: Decimal
    realized_pnl_ytd_pkr: Decimal
    dividends_ytd_pkr: Decimal
    fees_ytd_pkr: Decimal
    holding_count: int
