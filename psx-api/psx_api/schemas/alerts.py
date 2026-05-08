from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SuspiciousDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    alert_date: date
    alert_type: str
    severity: str
    vol_spike: Decimal
    price_change_pct: Decimal
    anomaly_score: Decimal | None
    has_news_context: bool
    explanation: str
    created_at: datetime


class StockSuspiciousState(BaseModel):
    """Latest suspicious-day flag, if any, surfaced on the stock detail page."""

    has_active_alert: bool
    latest: SuspiciousDayResponse | None = None
