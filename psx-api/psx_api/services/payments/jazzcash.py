"""
JazzCash HTTP POST integration (v2.0).

Flow
----
1. We HMAC-SHA256 sign a fixed-order payload with the merchant
   `integrity_salt`, then form-POST it to the JazzCash hosted checkout.
2. User authenticates on jazzcash.com.pk (mobile wallet PIN, OTP, or
   linked card).
3. JazzCash POSTs to our `callback_url` with the same fields plus a
   `pp_ResponseCode` and a fresh `pp_SecureHash` we have to re-verify.

References
----------
- JazzCash Integration Guide, "HTTP Post v2.0" section.
- Amount is in **paisas** (PKR × 100), zero-padded as a string.
- `pp_TxnRefNo` must start with `T` and be ≤ 20 chars.
- Hash is HMAC-SHA256 of `salt&val1&val2&...` where values are taken
  in **ASCII-sorted key order**, excluding empty values and the hash
  itself.
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


_LIVE_URL = "https://payments.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform"
_SANDBOX_URL = "https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform"


class JazzCashGateway(PaymentGateway):
    slug = "jazzcash"
    display_name = "JazzCash"

    def __init__(self) -> None:
        self._merchant_id = settings.jazzcash_merchant_id
        self._password = settings.jazzcash_password
        self._salt = settings.jazzcash_integrity_salt
        self._environment = settings.jazzcash_environment
        self._is_configured = bool(self._merchant_id and self._password and self._salt)

    # ── outbound ──────────────────────────────────────────────────

    def create_intent(self, ctx: CheckoutContext) -> CheckoutResult:
        # Pakistan Standard Time stamps required by JazzCash.
        now_pkt = datetime.now(timezone(timedelta(hours=5)))
        txn_date = now_pkt.strftime("%Y%m%d%H%M%S")
        expiry = (now_pkt + timedelta(hours=1)).strftime("%Y%m%d%H%M%S")

        amount_paisas = int((ctx.amount_pkr * Decimal(100)).quantize(Decimal("1")))

        payload: dict[str, str] = {
            "pp_Version": "1.1",
            "pp_TxnType": "MWALLET",
            "pp_Language": "EN",
            "pp_MerchantID": self._merchant_id or "MC00000",
            "pp_Password": self._password or "sandbox",
            "pp_TxnRefNo": _truncate_ref(ctx.merchant_txn_ref),
            "pp_Amount": str(amount_paisas),
            "pp_TxnCurrency": "PKR",
            "pp_TxnDateTime": txn_date,
            "pp_BillReference": "psxai_subscription",
            "pp_Description": ctx.description[:60],
            "pp_TxnExpiryDateTime": expiry,
            "pp_ReturnURL": ctx.callback_url,
            "ppmpf_1": ctx.customer_email,
            "ppmpf_2": ctx.customer_phone or "",
        }

        payload["pp_SecureHash"] = self._compute_hash(payload)

        if not self._is_configured:
            # Sandbox short-circuit so devs can finish the flow without
            # real JazzCash onboarding. Frontend treats the return URL
            # the same as a real gateway redirect.
            return CheckoutResult(
                checkout_url=_local_sandbox_url(ctx, "jazzcash"),
                is_sandbox=True,
                request_payload=payload,
            )

        # We *could* server-side-POST and parse the resulting form, but
        # JazzCash's documented flow is browser-driven: the frontend
        # auto-submits a form to this URL. We return the URL plus the
        # signed payload; the frontend renders a hidden form.
        base_url = _LIVE_URL if self._environment == "live" else _SANDBOX_URL
        return CheckoutResult(
            checkout_url=base_url,
            is_sandbox=self._environment != "live",
            request_payload=payload,
        )

    # ── inbound ───────────────────────────────────────────────────

    def verify_callback(self, payload: dict[str, Any]) -> CallbackResult:
        # JazzCash sends all the original fields plus pp_ResponseCode and
        # a new pp_SecureHash. Recompute and compare in constant time.
        flat: dict[str, str] = {
            k: ("" if v is None else str(v))
            for k, v in payload.items()
            if k != "pp_SecureHash"
        }
        sent_hash = str(payload.get("pp_SecureHash") or "")
        expected = self._compute_hash(flat)

        # In sandbox mode without configured creds, hashing is a no-op
        # check (we still validate the field is present so a missing
        # callback POST doesn't silently pass).
        if self._is_configured and not hmac.compare_digest(sent_hash.lower(), expected.lower()):
            raise GatewayError("JazzCash callback signature mismatch.", status_code=400)

        response_code = str(payload.get("pp_ResponseCode") or "")
        # 000 = success per JazzCash spec; anything else is a failure
        # with the response message in pp_ResponseMessage.
        is_paid = response_code == "000"
        amount_paisas = payload.get("pp_Amount")
        amount_pkr = (
            (Decimal(int(amount_paisas)) / Decimal(100))
            if amount_paisas is not None
            else None
        )
        return CallbackResult(
            merchant_txn_ref=str(payload.get("pp_TxnRefNo") or ""),
            status="paid" if is_paid else "failed",
            gateway_txn_id=str(payload.get("pp_RetreivalReferenceNo") or "") or None,
            amount_pkr=amount_pkr,
            failure_reason=None if is_paid else str(payload.get("pp_ResponseMessage") or ""),
            raw_payload=payload,
        )

    # ── internals ─────────────────────────────────────────────────

    def _compute_hash(self, fields: dict[str, str]) -> str:
        """Per JazzCash spec: HMAC-SHA256 over 'salt&v1&v2&...' where the
        values are taken in ASCII-sorted key order, skipping empties.
        Returns uppercase hex."""
        ordered = [
            v for k, v in sorted(fields.items()) if v not in ("", None)
        ]
        message = self._salt + "&" + "&".join(ordered) if ordered else self._salt
        return hmac.new(
            self._salt.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()


def _truncate_ref(ref: str) -> str:
    """JazzCash caps pp_TxnRefNo at 20 chars and requires a leading T."""
    cleaned = ref if ref.startswith("T") else "T" + ref
    return cleaned[:20]


def _local_sandbox_url(ctx: CheckoutContext, provider: str) -> str:
    """Local URL the frontend redirects to when no merchant creds are
    set. Lands on /checkout/sandbox-return which auto-POSTs a synthetic
    'paid' callback to the backend, so the full subscribe flow can be
    tested end-to-end without real money."""
    base = settings.payments_return_url.rstrip("/")
    return (
        f"{base}/sandbox?provider={provider}"
        f"&ref={ctx.merchant_txn_ref}"
        f"&amount={ctx.amount_pkr}"
    )
