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


class HoldingDashboardRow(BaseModel):
    symbol: str
    company_name: str
    sector: str
    is_kmi_compliant: bool
    quantity: Decimal
    avg_cost_pkr: Decimal
    total_invested_pkr: Decimal
    last_close: Decimal | None
    last_close_date: date | None
    market_value_pkr: Decimal | None
    unrealized_pnl_pkr: Decimal | None
    unrealized_pnl_pct: Decimal | None
    day_change_pct: Decimal | None
    realized_pnl_pkr: Decimal
    total_dividends_received_pkr: Decimal


class SectorAllocationRow(BaseModel):
    sector: str
    value_pkr: Decimal
    pct: Decimal


class PortfolioSummary(BaseModel):
    """High-level rollup for the dashboard."""

    portfolio_id: str
    total_invested_pkr: Decimal
    current_value_pkr: Decimal
    unrealized_pnl_pkr: Decimal
    unrealized_pnl_pct: Decimal
    # The differentiator: P&L net of CGT-if-sold-today
    unrealized_pnl_after_tax_pkr: Decimal
    estimated_liquidation_cgt_pkr: Decimal
    realized_pnl_ytd_pkr: Decimal
    dividends_ytd_pkr: Decimal
    fees_ytd_pkr: Decimal
    holding_count: int
    holdings: list[HoldingDashboardRow]
    sector_allocation: list[SectorAllocationRow]


# ── Trade-entry preview (Step 23 confirmation step) ────────────────────


class MatchedLotPreview(BaseModel):
    """One buy lot consumed by a sell, for the confirmation step's lot table."""

    transaction_id: str | None = None  # None for unsaved preview
    buy_date: date
    quantity: Decimal
    buy_price: Decimal
    holding_period_days: int
    gross_gain_pkr: Decimal
    cgt_rate_pct: Decimal
    cgt_pkr: Decimal


class TransactionPreview(BaseModel):
    """
    Result of `POST /portfolios/{id}/transactions/preview` — the modal's
    confirmation step calls this before save to show the user exactly what
    the trade will cost in PKR (gross, every charge, net cash impact).
    """

    transaction_type: TransactionTypeLiteral
    symbol: str
    quantity: Decimal
    price_per_share: Decimal
    gross_value_pkr: Decimal
    brokerage_pkr: Decimal
    fed_pkr: Decimal
    cvt_pkr: Decimal
    cgt_pkr: Decimal  # 0 for non-sells
    total_charges_pkr: Decimal
    net_cash_impact_pkr: Decimal  # negative for buys, positive for sells
    # Sells only: which buy lots get consumed FIFO and the per-lot CGT
    matched_lots: list[MatchedLotPreview] = []
    # If this is a sell that exceeds open lots, errors describe the issue
    warnings: list[str] = []
