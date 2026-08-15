"""
Pakistani payment-gateway adapters.

Each gateway implements the `PaymentGateway` protocol from `base.py`:
- `create_intent(intent, ...)` — turn our PaymentIntent row into a
  checkout URL the user is redirected to, signed with the gateway's
  merchant secret.
- `verify_callback(payload)` — when the gateway POSTs back, validate
  the signature and parse the result into a structured `CallbackResult`.

If merchant credentials aren't set (env vars empty), each gateway
returns `sandbox_url=True` so the full flow works in dev without
needing real onboarding. Flip to live by setting the creds and the
`*_environment=live` env var.

Coverage:
- **JazzCash** — mobile wallet + card (HBL Pay backbone). HMAC-SHA256.
- **Easypaisa** — Telenor Microfinance Bank wallet + OTC. HMAC-SHA256.
- **Meezan Bank IPG** — bank-direct card processing for the Shariah-
  conscious user base. MD5/SHA hash.
- **1LINK PayFast** — aggregator that fronts Allied, HBL, UBL, Alfalah,
  MCB, BAFL, etc. through a single integration. HMAC-SHA256.
- **SafePay** — local Stripe-equivalent REST API.
- **NayaPay** — wallet, popular with younger users.
- **manual** — fallback: returns IBAN/account-number instructions for
  off-platform bank transfer, plus a follow-up email trigger.
"""

from __future__ import annotations

from psx_api.services.payments.allied_payfast import AlliedPayFastGateway
from psx_api.services.payments.base import (
    CallbackResult,
    CheckoutContext,
    CheckoutResult,
    GatewayError,
    PaymentGateway,
)
from psx_api.services.payments.easypaisa import EasypaisaGateway
from psx_api.services.payments.jazzcash import JazzCashGateway
from psx_api.services.payments.manual import ManualBankTransferGateway
from psx_api.services.payments.meezan import MeezanIPGGateway
from psx_api.services.payments.nayapay import NayaPayGateway
from psx_api.services.payments.safepay import SafePayGateway

# Provider slug → constructor. Keep slugs in sync with the
# `ck_payment_intents_provider` CHECK in migration 0015.
_REGISTRY: dict[str, type[PaymentGateway]] = {
    "jazzcash": JazzCashGateway,
    "easypaisa": EasypaisaGateway,
    "meezan": MeezanIPGGateway,
    "allied_payfast": AlliedPayFastGateway,
    "safepay": SafePayGateway,
    "nayapay": NayaPayGateway,
    "manual": ManualBankTransferGateway,
}


def get_gateway(provider: str) -> PaymentGateway:
    if provider not in _REGISTRY:
        raise GatewayError(
            f"Unknown payment provider '{provider}'. " f"Supported: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[provider]()


def supported_providers() -> list[dict[str, str]]:
    """Public-facing list shown on the checkout page."""
    return [
        {
            "slug": "jazzcash",
            "name": "JazzCash",
            "category": "wallet",
            "description": "Pay with your JazzCash mobile wallet or linked card.",
            "logo_hint": "jazzcash",
        },
        {
            "slug": "easypaisa",
            "name": "Easypaisa",
            "category": "wallet",
            "description": "Pay with your Easypaisa account or OTC at any agent.",
            "logo_hint": "easypaisa",
        },
        {
            "slug": "meezan",
            "name": "Meezan Bank",
            "category": "bank",
            "description": "Direct bank checkout via Meezan IPG (Islamic banking).",
            "logo_hint": "meezan",
        },
        {
            "slug": "allied_payfast",
            "name": "Allied / HBL / UBL / Alfalah (via 1LINK)",
            "category": "bank",
            "description": "Pay with any 1LINK-enabled Pakistani bank card via PayFast.",
            "logo_hint": "1link",
        },
        {
            "slug": "safepay",
            "name": "SafePay (Card)",
            "category": "card",
            "description": "Visa / Mastercard processing via SafePay.",
            "logo_hint": "safepay",
        },
        {
            "slug": "nayapay",
            "name": "NayaPay",
            "category": "wallet",
            "description": "Pay with your NayaPay wallet.",
            "logo_hint": "nayapay",
        },
        {
            "slug": "manual",
            "name": "Bank transfer (manual)",
            "category": "manual",
            "description": "Email-based bank transfer. Activation within 24h on confirmation.",
            "logo_hint": "bank",
        },
    ]


__all__ = [
    "CallbackResult",
    "CheckoutContext",
    "CheckoutResult",
    "GatewayError",
    "PaymentGateway",
    "get_gateway",
    "supported_providers",
]
