"""
SafePay — local Pakistani "Stripe-equivalent" REST API.

Flow
----
1. We POST a JSON tracker request to `/order/payments/v3/`.
2. SafePay returns a `tracker.token`; we redirect the user to
   `getsafepay.com/checkout/pay?env=...&beacon=<token>...`.
3. SafePay POSTs a signed webhook to our callback URL with the result.

Webhook signatures are HMAC-SHA256 of the raw body keyed by the
`webhook_secret`. SafePay sends it in the `X-SFPY-SIGNATURE` header.
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

_LIVE_CHECKOUT = "https://getsafepay.com/checkout/pay"
_SANDBOX_CHECKOUT = "https://sandbox.api.getsafepay.com/checkout/pay"


class SafePayGateway(PaymentGateway):
    slug = "safepay"
    display_name = "SafePay (Card)"

    def __init__(self) -> None:
        self._api_key = settings.safepay_api_key
        self._webhook_secret = settings.safepay_webhook_secret
        self._environment = settings.safepay_environment
        self._is_configured = bool(self._api_key and self._webhook_secret)

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        # Real SafePay integration would HTTP POST to their tracker
        # endpoint and parse the returned tracker token. We capture the
        # request body so the audit row has the same shape it'd have
        # against the real API, and synthesize a sandbox redirect.
        payload = {
            "amount": int(ctx.amount_pkr * 100),  # paisas
            "currency": "PKR",
            "order_id": ctx.merchant_txn_ref,
            "customer_email": ctx.customer_email,
            "customer_phone": ctx.customer_phone or "",
            "redirect_url": ctx.return_url,
            "cancel_url": ctx.return_url + "?canceled=1",
            "webhook_url": ctx.callback_url,
            "description": ctx.description,
        }

        if not self._is_configured:
            return CheckoutResult(
                checkout_url=_local_sandbox_url(ctx, "safepay"),
                is_sandbox=True,
                request_payload=payload,
            )

        # Live integration: real HTTP call goes here. We model the URL
        # build so the contract is honoured; in prod swap in `httpx`.
        base = _LIVE_CHECKOUT if self._environment == "live" else _SANDBOX_CHECKOUT
        env_param = "production" if self._environment == "live" else "sandbox"
        checkout_url = (
            f"{base}?env={env_param}" f"&order_id={ctx.merchant_txn_ref}" f"&source=custom"
        )
        return CheckoutResult(
            checkout_url=checkout_url,
            is_sandbox=self._environment != "live",
            request_payload=payload,
        )

    def verify_callback(self, payload: dict[str, Any]) -> CallbackResult:
        # SafePay webhooks are signed over the raw JSON body. The
        # signature is read from the X-SFPY-SIGNATURE request header
        # and passed in as `_signature`/`_raw_body` by the router.
        signature = str(payload.pop("_signature", "") or "")
        raw_body = payload.pop("_raw_body", None)
        body_bytes = (
            raw_body
            if isinstance(raw_body, bytes | bytearray)
            else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )

        expected = hmac.new(
            self._webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()

        if self._is_configured and not hmac.compare_digest(signature.lower(), expected.lower()):
            raise GatewayError("SafePay webhook signature mismatch.", status_code=400)

        data = payload.get("data") or payload
        status_raw = str(data.get("state") or data.get("status") or "").lower()
        status: Any
        if status_raw in ("paid", "succeeded", "tracker_paid"):
            status = "paid"
        elif status_raw in ("canceled", "cancelled", "tracker_canceled"):
            status = "canceled"
        elif status_raw in ("pending", "tracker_pending"):
            status = "pending"
        else:
            status = "failed"

        amount = data.get("amount") or data.get("amount_paid")
        amount_pkr = (
            Decimal(int(amount)) / Decimal(100)
            if isinstance(amount, int | float | str) and str(amount).isdigit()
            else (Decimal(str(amount)) if amount else None)
        )

        return CallbackResult(
            merchant_txn_ref=str(data.get("order_id") or ""),
            status=status,
            gateway_txn_id=str(data.get("token") or data.get("tracker") or "") or None,
            amount_pkr=amount_pkr,
            failure_reason=str(data.get("error") or "") if status == "failed" else None,
            raw_payload=payload,
        )
