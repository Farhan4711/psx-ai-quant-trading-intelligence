"""
Meezan Bank Internet Payment Gateway (IPG).

Meezan's IPG is a redirect-then-callback flow signed with SHA-256
(older versions used MD5; Meezan migrated production to SHA-256 in
2023). The Shariah-conscious user base prefers this over JazzCash
because the underlying clearing is via Meezan Bank (Islamic banking).

Flow
----
1. We compute a SHA-256 hex of `secret_key + merchant_id + txn_ref
   + amount + currency` and POST it together with the order data to
   Meezan's hosted form.
2. User authenticates with their card OTP.
3. Meezan redirects back with `OrderId`, `RC` (response code), `TID`,
   `Hash` for us to verify (recomputed with the response hash spec).
"""

from __future__ import annotations

import hashlib
import hmac
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

_LIVE_URL = "https://ipg.meezanbank.com/IPGGenericIntegration/Index.jsf"
_SANDBOX_URL = "https://ipgtest.meezanbank.com/IPGGenericIntegration/Index.jsf"


class MeezanIPGGateway(PaymentGateway):
    slug = "meezan"
    display_name = "Meezan Bank IPG"

    def __init__(self) -> None:
        self._merchant_id = settings.meezan_merchant_id
        self._secret = settings.meezan_secret_key
        self._environment = settings.meezan_environment
        self._is_configured = bool(self._merchant_id and self._secret)

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        amount = f"{ctx.amount_pkr:.2f}"
        # Meezan request hash spec: SHA256(secret|merchant|ref|amount|PKR|return_url)
        hash_input = (
            f"{self._secret}|{self._merchant_id}|{ctx.merchant_txn_ref}|"
            f"{amount}|PKR|{ctx.callback_url}"
        )
        request_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        payload: dict[str, str] = {
            "MerchantID": self._merchant_id or "TEST_MEEZAN",
            "OrderId": ctx.merchant_txn_ref,
            "Amount": amount,
            "Currency": "PKR",
            "CustomerEmail": ctx.customer_email,
            "CustomerMobile": ctx.customer_phone or "",
            "Description": ctx.description[:100],
            "ReturnURL": ctx.callback_url,
            "Hash": request_hash,
        }

        if not self._is_configured:
            return CheckoutResult(
                checkout_url=_local_sandbox_url(ctx, "meezan"),
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
        # Response hash spec: SHA256(secret|merchant|orderid|amount|RC|TID)
        order_id = str(payload.get("OrderId") or "")
        amount = str(payload.get("Amount") or "")
        rc = str(payload.get("RC") or "")
        tid = str(payload.get("TID") or "")
        sent_hash = str(payload.get("Hash") or "")

        expected_input = f"{self._secret}|{self._merchant_id}|{order_id}|{amount}|{rc}|{tid}"
        expected = hashlib.sha256(expected_input.encode("utf-8")).hexdigest()

        if self._is_configured and not hmac.compare_digest(sent_hash.lower(), expected.lower()):
            raise GatewayError("Meezan callback hash mismatch.", status_code=400)

        is_paid = rc == "00"
        return CallbackResult(
            merchant_txn_ref=order_id,
            status="paid" if is_paid else "failed",
            gateway_txn_id=tid or None,
            amount_pkr=Decimal(amount) if amount else None,
            failure_reason=None if is_paid else str(payload.get("ResponseDescription") or rc),
            raw_payload=payload,
        )
