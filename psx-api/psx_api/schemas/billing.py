from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SubscriptionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    tagline: str
    price_pkr_monthly: Decimal
    price_pkr_annual: Decimal | None
    features: list[str]
    display_order: int


class CurrentSubscriptionResponse(BaseModel):
    plan: SubscriptionPlanResponse
    status: str
    period_start: date | None = None
    period_end: date | None = None
    cancel_at_period_end: bool = False


class CheckoutResponse(BaseModel):
    """Returned by /billing/subscribe — payload the UI uses to continue checkout."""

    provider: str
    plan_slug: str
    amount_pkr_monthly: str
    checkout_url: str | None
    message: str
