"""
Manual bank-transfer fallback.

Used when:
- The user can't or won't use any of the digital gateways
- We're testing locally without any merchant onboarding done

`create_intent` returns plain-text bank-transfer instructions. The
`verify_callback` is admin-driven: a privileged endpoint marks the
intent paid once we eyeball the bank statement.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from psx_api.services.payments.base import (
    CallbackResult,
    CheckoutContext,
    CheckoutResult,
    PaymentGateway,
)


_INSTRUCTIONS_TEMPLATE = """
Please transfer **PKR {amount}** to the following account and email
your receipt + this reference number to **hello@psxai.example**:

    Bank: Meezan Bank Limited
    Account title: PSX AI (Pvt) Ltd
    Account #: [PLACEHOLDER — to be filled by ops]
    IBAN: [PLACEHOLDER]

    Reference: {ref}

We typically activate accounts within 4 business hours after receipt.
""".strip()


class ManualBankTransferGateway(PaymentGateway):
    slug = "manual"
    display_name = "Bank transfer (manual)"

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        instructions = _INSTRUCTIONS_TEMPLATE.format(
            amount=f"{ctx.amount_pkr:.2f}",
            ref=ctx.merchant_txn_ref,
        )
        return CheckoutResult(
            # Manual gateway has no hosted page; the frontend renders
            # the instructions inline. We still return a URL pointing
            # at the confirmation screen for consistency.
            checkout_url=ctx.return_url + "?manual=1&ref=" + ctx.merchant_txn_ref,
            is_sandbox=False,
            request_payload={
                "amount_pkr": str(ctx.amount_pkr),
                "merchant_txn_ref": ctx.merchant_txn_ref,
            },
            instructions=instructions,
        )

    def verify_callback(self, payload: dict[str, Any]) -> CallbackResult:
        # Admin-driven only — see /billing/admin/confirm-manual endpoint.
        # We trust the admin caller here; auth is enforced at the router.
        amount = payload.get("amount_pkr")
        return CallbackResult(
            merchant_txn_ref=str(payload.get("merchant_txn_ref") or ""),
            status="paid",
            gateway_txn_id=str(payload.get("bank_ref") or "") or None,
            amount_pkr=Decimal(str(amount)) if amount else None,
            raw_payload=payload,
        )
