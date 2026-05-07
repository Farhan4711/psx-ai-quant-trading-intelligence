from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SecurityBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)
    sector: str = Field(..., min_length=1, max_length=100)
    is_kmi_compliant: bool = False
    is_kse100: bool = False
    is_kse30: bool = False
    market_cap_pkr: int | None = None
    shares_outstanding: int | None = None
    listed_at: date | None = None
    delisted_at: date | None = None
    is_active: bool = True

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, value: str) -> str:
        return value.upper().strip()


class SecurityCreate(SecurityBase):
    pass


class SecurityUpdate(BaseModel):
    company_name: str | None = None
    sector: str | None = None
    is_kmi_compliant: bool | None = None
    is_kse100: bool | None = None
    is_kse30: bool | None = None
    market_cap_pkr: int | None = None
    shares_outstanding: int | None = None
    is_active: bool | None = None


class SecurityResponse(SecurityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime


class SecuritiesListResponse(BaseModel):
    items: list[SecurityResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class OhlcvResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None
    value_pkr: Decimal | None
    adjusted_close: Decimal | None


class OhlcvListResponse(BaseModel):
    symbol: str
    interval: str
    items: list[OhlcvResponse]
    total: int


class FundamentalsResponse(BaseModel):
    symbol: str
    # Computed from OHLCV
    week_52_high: Decimal | None
    week_52_low: Decimal | None
    avg_volume_30d: int | None
    # From securities table
    market_cap_pkr: int | None
    shares_outstanding: int | None
    # Placeholders — populated once financial statement data is available (Phase 2)
    pe_ratio: Decimal | None = None
    pb_ratio: Decimal | None = None
    eps: Decimal | None = None
    roe: Decimal | None = None
    dividend_yield: Decimal | None = None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    action_type: str
    announcement_date: date
    ex_date: date | None
    record_date: date | None
    payment_date: date | None
    amount_per_share: Decimal | None
    ratio_numerator: int | None
    ratio_denominator: int | None


class AnnouncementsListResponse(BaseModel):
    symbol: str
    items: list[AnnouncementResponse]
    total: int


class IndexPerformance(BaseModel):
    name: str           # "KSE-100", "KSE-30", "KMI-30"
    constituent_count: int
    # Latest trading day stats — None until OHLCV data is loaded
    last_close_date: date | None
    change_1d_pct: Decimal | None
    change_1w_pct: Decimal | None
    change_1m_pct: Decimal | None
    change_ytd_pct: Decimal | None


class WatchlistItemResponse(BaseModel):
    symbol: str
    company_name: str
    sector: str
    is_kmi_compliant: bool
    note: str | None
    sort_order: int
    added_at: datetime


class WatchlistReorderRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=0, max_length=500)


class Quote(BaseModel):
    symbol: str
    last_close: Decimal | None
    prev_close: Decimal | None
    last_date: date | None
    change: Decimal | None
    change_pct: Decimal | None


class QuotesResponse(BaseModel):
    items: list[Quote]
