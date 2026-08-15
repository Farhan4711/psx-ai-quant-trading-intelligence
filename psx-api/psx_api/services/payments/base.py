"""
Payment gateway contract.

Each Pakistani gateway implements `PaymentGateway`. We deliberately don't
inherit from anything heavy (no abstract enforcement via `abc` here) —
keep adapters tiny and testable. The protocol is enforced by the
registry in `__init__.py` and by tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Protocol


class GatewayError(Exception):
    """Raised when a gateway can't be used (bad config, signing failure,
    refused by upstream). The HTTP layer turns this into a 502/400."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class CheckoutContext:
    """Everything a gateway needs to spin up a checkout."""

    merchant_txn_ref: str
    amount_pkr: Decimal
    description: str
    customer_email: str
    customer_name: str | None
    customer_phone: str | None
    return_url: str  # frontend page user lands on after gateway
    callback_url: str  # backend webhook the gateway POSTs to
    expires_at_unix: int  # epoch seconds


@dataclass(slots=True)
class CheckoutResult:
    """What the API returns to the frontend after creating a checkout."""

    # For redirect-based gateways (JazzCash/Easypaisa/Meezan/PayFast):
    # the frontend does `window.location = checkout_url`. For API-based
    # gateways (SafePay/NayaPay): same — they all reduce to a hosted URL.
    checkout_url: str
    # Whether this is a real gateway response or a local sandbox stub.
    # The UI shows a "DEV — no real payment will be taken" banner when true.
    is_sandbox: bool
    # Raw request we built (stored on the PaymentIntent for audit).
    request_payload: dict[str, Any]
    # Optional: the gateway's own txn ID returned on creation (some
    # gateways assign it synchronously, others only on callback).
    gateway_txn_id: str | None = None
    # For manual/bank-transfer flows the gateway returns inline
    # instructions instead of a hosted page.
    instructions: str | None = None


CallbackStatus = Literal["paid", "failed", "canceled", "pending"]


@dataclass(slots=True)
class CallbackResult:
    """Normalised view of a gateway callback."""

    merchant_txn_ref: str
    status: CallbackStatus
    gateway_txn_id: str | None
    amount_pkr: Decimal | None
    failure_reason: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class PaymentGateway(Protocol):
    slug: str
    display_name: str

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        """Build the gateway-side checkout and return the redirect URL."""
        ...

    def verify_callback(self, payload: dict[str, Any]) -> CallbackResult:
        """Validate signature on a callback/webhook POST and normalise it.

        MUST raise `GatewayError` if the signature doesn't verify. Callers
        will activate the subscription based on the parsed status, so a
        forged callback that passes here = silent free Pro for the
        attacker."""
        ...
