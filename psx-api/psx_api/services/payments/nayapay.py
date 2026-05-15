"""
NayaPay — wallet API for younger Pakistani users.

REST-style integration similar to SafePay: API key for outbound,
HMAC-SHA256 webhook signature in `X-NP-Signature`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
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


_LIVE_CHECKOUT = "https://api.nayapay.com/checkout/v1/pay"
_SANDBOX_CHECKOUT = "https://sandbox.nayapay.com/checkout/v1/pay"


class NayaPayGateway(PaymentGateway):
    slug = "nayapay"
    display_name = "NayaPay"

    def __init__(self) -> None:
        self._api_key = settings.nayapay_api_key
        self._webhook_secret = settings.nayapay_webhook_secret
        self._environment = settings.nayapay_environment
        self._is_configured = bool(self._api_key and self._webhook_secret)

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        payload = {
            "amount_paisas": int(ctx.amount_pkr * 100),
            "currency": "PKR",
            "merchant_reference": ctx.merchant_txn_ref,
            "customer": {
                "email": ctx.customer_email,
                "phone": ctx.customer_phone or "",
                "name": ctx.customer_name or ctx.customer_email,
            },
            "callbacks": {
                "success_url": ctx.return_url,
                "cancel_url": ctx.return_url + "?canceled=1",
                "webhook_url": ctx.callback_url,
            },
            "description": ctx.description,
        }

        if not self._is_configured:
            return CheckoutResult(
                checkout_url=_local_sandbox_url(ctx, "nayapay"),
                is_sandbox=True,
                request_payload=payload,
            )

        base = _LIVE_CHECKOUT if self._environment == "live" else _SANDBOX_CHECKOUT
        return CheckoutResult(
            checkout_url=f"{base}?ref={ctx.merchant_txn_ref}",
            is_sandbox=self._environment != "live",
            request_payload=payload,
        )

    def verify_callback(self, payload: dict[str, Any]) -> CallbackResult:
        signature = str(payload.pop("_signature", "") or "")
        raw_body = payload.pop("_raw_body", None)
        body_bytes = (
            raw_body
            if isinstance(raw_body, (bytes, bytearray))
            else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        expected = hmac.new(
            self._webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if self._is_configured and not hmac.compare_digest(signature.lower(), expected.lower()):
            raise GatewayError("NayaPay webhook signature mismatch.", status_code=400)

        status_raw = str(payload.get("status") or "").lower()
        status: Any = (
            "paid" if status_raw == "completed"
            else "canceled" if status_raw == "cancelled"
            else "pending" if status_raw == "pending"
            else "failed"
        )
        amount_paisas = payload.get("amount_paisas")
        amount_pkr = (
            Decimal(int(amount_paisas)) / Decimal(100)
            if amount_paisas is not None else None
        )
        return CallbackResult(
            merchant_txn_ref=str(payload.get("merchant_reference") or ""),
            status=status,
            gateway_txn_id=str(payload.get("transaction_id") or "") or None,
            amount_pkr=amount_pkr,
            failure_reason=str(payload.get("error_message") or "") if status == "failed" else None,
            raw_payload=payload,
        )
