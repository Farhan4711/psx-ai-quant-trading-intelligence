"""
1LINK PayFast — covers Allied Bank (ABL), HBL, UBL, Bank Alfalah, MCB,
BAFL, Faysal, etc. through a single integration.

Why PayFast for "Allied"
------------------------
ABL's own merchant portal still routes through PCS/1LINK aggregators,
and PayFast is the most commonly used aggregator for retail SaaS in
Pakistan today. Going PayFast = ABL + every other major bank without
N separate onboarding cycles.

Flow
----
1. We HMAC-SHA256 sign the form payload with `secret_key` and POST it
   to PayFast hosted checkout.
2. User picks their bank and authenticates (3DS / OTP).
3. PayFast redirects back with txn fields + signature; we verify.

Reference: 1LINK PayFast Merchant Integration Manual v2.1.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from psx_api.config import settings
from psx_api.services.payments.base import (
    CallbackResult,
    CheckoutContext,
    CheckoutResult,
    GatewayError,
    PaymentGateway,
)
from psx_api.services.payments.jazzcash import _local_sandbox_url

_LIVE_URL = "https://payfast.1link.net.pk/PayFast/Checkout"
_SANDBOX_URL = "https://payfaststg.1link.net.pk/PayFast/Checkout"


class AlliedPayFastGateway(PaymentGateway):
    slug = "allied_payfast"
    display_name = "Allied / HBL / UBL / Alfalah (via 1LINK PayFast)"

    def __init__(self) -> None:
        self._merchant_id = settings.payfast_merchant_id
        self._secret = settings.payfast_secret_key
        self._environment = settings.payfast_environment
        self._is_configured = bool(self._merchant_id and self._secret)

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        now_pkt = datetime.now(timezone(timedelta(hours=5)))
        ts = now_pkt.strftime("%Y%m%d%H%M%S")

        payload: dict[str, str] = {
            "MERCHANT_ID": self._merchant_id or "MERCHANT123",
            "TRANSACTION_ID": ctx.merchant_txn_ref,
            "TRANSACTION_AMOUNT": f"{ctx.amount_pkr:.2f}",
            "TRANSACTION_CURRENCY": "PKR",
            "TRANSACTION_DATETIME": ts,
            "PRODUCT_DESCRIPTION": ctx.description[:100],
            "CUSTOMER_EMAIL_ADDRESS": ctx.customer_email,
            "CUSTOMER_MOBILE_NO": ctx.customer_phone or "",
            "RESPONSE_URL": ctx.callback_url,
            "VERSION": "1.0",
        }

        payload["SIGNATURE"] = self._sign(payload)

        if not self._is_configured:
            return CheckoutResult(
                checkout_url=_local_sandbox_url(ctx, "allied_payfast"),
                is_sandbox=True,
                request_payload=payload,
            )

        base = _LIVE_URL if self._environment == "live" else _SANDBOX_URL
        return CheckoutResult(
            checkout_url=base,
            is_sandbox=self._environment != "live",
            request_payload=payload,
        )

    def verify_callback(self, payload: dict[str, Any]) -> CallbackResult:
        flat: dict[str, str] = {
            k: ("" if v is None else str(v)) for k, v in payload.items() if k != "SIGNATURE"
        }
        sent = str(payload.get("SIGNATURE") or "")
        expected = self._sign(flat)
        if self._is_configured and not hmac.compare_digest(sent.lower(), expected.lower()):
            raise GatewayError("PayFast callback signature mismatch.", status_code=400)

        rc = str(payload.get("RESPONSE_CODE") or "")
        is_paid = rc == "00"
        amount = payload.get("TRANSACTION_AMOUNT")
        return CallbackResult(
            merchant_txn_ref=str(payload.get("TRANSACTION_ID") or ""),
            status="paid" if is_paid else "failed",
            gateway_txn_id=str(payload.get("REFERENCE_NUMBER") or "") or None,
            amount_pkr=Decimal(str(amount)) if amount else None,
            failure_reason=None if is_paid else str(payload.get("RESPONSE_MESSAGE") or rc),
            raw_payload=payload,
        )

    def _sign(self, fields: dict[str, str]) -> str:
        """HMAC-SHA256 over 'k1=v1&k2=v2&...' in ASCII key order."""
        message = "&".join(f"{k}={fields[k]}" for k in sorted(fields) if fields[k])
        return (
            hmac.new(
                self._secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )
