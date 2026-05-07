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
