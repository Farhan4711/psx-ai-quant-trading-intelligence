"""
Easypaisa (Telenor Microfinance Bank) — Easypay redirect integration.

Flow
----
1. We HMAC-SHA256 sign the payload with the merchant `hash_key`.
2. User is redirected to easypay.easypaisa.com.pk to authenticate
   (mobile wallet PIN, OTP) or pay cash OTC at any Easypaisa agent.
3. Easypaisa redirects back with `paymentToken`, `orderRefNum`,
   `status`, and `merchantHashedReq` we have to verify.

Reference
---------
Easypay Merchant Integration Guide:
- Amount in PKR with 2 decimals as a string ("900.00").
- Hash is HMAC-SHA256(hash_key, "key1=val1&key2=val2&...") with the
  fields in a documented order, base64-encoded.
"""

from __future__ import annotations

import base64
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


_LIVE_URL = "https://easypay.easypaisa.com.pk/easypay/Index.jsf"
_SANDBOX_URL = "https://easypaystg.easypaisa.com.pk/easypay/Index.jsf"

# Order Easypay expects for the request hash (per merchant guide).
_REQUEST_HASH_ORDER = (
    "amount",
    "autoRedirect",
    "emailAddr",
    "expiryDate",
    "mobileNum",
    "orderRefNum",
    "paymentMethod",
    "postBackURL",
    "storeId",
    "merchantPaymentMethod",
)


class EasypaisaGateway(PaymentGateway):
    slug = "easypaisa"
    display_name = "Easypaisa"

    def __init__(self) -> None:
        self._store_id = settings.easypaisa_store_id
        self._hash_key = settings.easypaisa_hash_key
        self._environment = settings.easypaisa_environment
        self._is_configured = bool(self._store_id and self._hash_key)

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        # Easypay wants dd-MM-yyyy HH:mm:ss in PKT.
        now_pkt = datetime.now(timezone(timedelta(hours=5)))
        expiry = (now_pkt + timedelta(hours=1)).strftime("%d-%m-%Y %H:%M:%S")

        payload: dict[str, str] = {
            "storeId": self._store_id or "12345",
            "orderRefNum": ctx.merchant_txn_ref,
            "amount": _format_amount(ctx.amount_pkr),
            "paymentMethod": "CC_PAYMENT_METHOD",        # CC = card, MA = mobile account
            "merchantPaymentMethod": "OTC_PAYMENT_METHOD",
            "emailAddr": ctx.customer_email,
            "mobileNum": ctx.customer_phone or "",
            "postBackURL": ctx.callback_url,
            "autoRedirect": "1",
            "expiryDate": expiry,
        }

        payload["merchantHashedReq"] = self._compute_hash(payload, _REQUEST_HASH_ORDER)

        if not self._is_configured:
            return CheckoutResult(
                checkout_url=_local_sandbox_url(ctx, "easypaisa"),
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
            k: ("" if v is None else str(v))
            for k, v in payload.items()
            if k != "merchantHashedReq"
        }
        sent_hash = str(payload.get("merchantHashedReq") or "")

        # Easypaisa sends back a slightly different field set in the
        # response hash; use the keys that are actually present.
        response_order = tuple(sorted(flat.keys()))
        expected = self._compute_hash(flat, response_order)
        if self._is_configured and not hmac.compare_digest(sent_hash, expected):
            raise GatewayError("Easypaisa callback signature mismatch.", status_code=400)

        # Status codes: 0000 = success, anything else = failure with
        # `responseDesc` containing the human reason.
        status_code = str(payload.get("status") or payload.get("responseCode") or "")
        is_paid = status_code == "0000"
        amount = payload.get("amount") or payload.get("transactionAmount")
        return CallbackResult(
            merchant_txn_ref=str(payload.get("orderRefNum") or ""),
            status="paid" if is_paid else "failed",
            gateway_txn_id=str(payload.get("paymentToken") or "") or None,
            amount_pkr=Decimal(str(amount)) if amount is not None else None,
            failure_reason=None if is_paid else str(payload.get("responseDesc") or ""),
            raw_payload=payload,
        )

    # ── internals ────────────────────────────────────────────────

    def _compute_hash(self, fields: dict[str, str], order: tuple[str, ...]) -> str:
        # "&".join(f"{k}={v}" for k in order if fields.get(k))
        message = "&".join(
            f"{k}={fields[k]}" for k in order if fields.get(k)
        )
        digest = hmac.new(
            self._hash_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("ascii")


def _format_amount(amount_pkr: Decimal) -> str:
    return f"{amount_pkr:.2f}"
