from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


PaymentProvider = Literal[
    "jazzcash",
    "easypaisa",
    "meezan",
    "allied_payfast",
    "safepay",
    "nayapay",
    "manual",
]

BillingCycle = Literal["monthly", "annual"]


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


class PaymentMethodOption(BaseModel):
    """One row on the checkout page's "Pay with…" picker."""

    slug: PaymentProvider
    name: str
    category: Literal["wallet", "bank", "card", "manual"]
    description: str
    logo_hint: str


class CheckoutRequest(BaseModel):
    plan_slug: str = Field(..., examples=["pro"])
    provider: PaymentProvider
    billing_cycle: BillingCycle = "monthly"


class CheckoutResponse(BaseModel):
    """Returned by /billing/checkout — payload the UI uses to continue."""

    intent_id: str
    provider: PaymentProvider
    checkout_url: str
    is_sandbox: bool
    instructions: str | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)
    amount_pkr: str
    expires_at: str | None = None


class PaymentIntentStatus(BaseModel):
    """Status polled by the frontend after a redirect to know whether
    activation succeeded — keeps the return page robust against the
    gateway-callback timing race."""

    id: str
    provider: PaymentProvider
    status: Literal[
        "pending", "redirected", "paid", "failed", "canceled", "expired"
    ]
    amount_pkr: str
    billing_cycle: BillingCycle
    plan_slug: str
    failure_reason: str | None = None
    created_at: datetime
    returned_at: datetime | None = None
