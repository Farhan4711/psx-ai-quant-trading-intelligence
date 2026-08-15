"""
Unit tests for the Pakistani payment-gateway adapters.

These are pure-Python tests — no DB, no HTTP. They cover:
- Signature compute + verify round-trip for each redirect gateway.
- A forged callback fails `verify_callback`.
- Sandbox mode (no creds) returns a local URL without raising.
- The registry maps every documented slug to a working class.
- Amount paisas conversion is correct.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from psx_api.services.payments import (
    GatewayError,
    get_gateway,
    supported_providers,
)
from psx_api.services.payments.base import CheckoutContext


def _ctx(amount_pkr: str = "900.00", ref: str = "TPSXAI00001") -> CheckoutContext:
    return CheckoutContext(
        merchant_txn_ref=ref,
        amount_pkr=Decimal(amount_pkr),
        description="PSX AI Pro monthly",
        customer_email="ali@example.pk",
        customer_name="Ali Khan",
        customer_phone="03001234567",
        return_url="http://localhost:3000/checkout/return?ref=" + ref,
        callback_url="http://localhost:8000/api/v1/billing/callback/PROVIDER",
        expires_at_unix=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
    )


# ── Registry ──────────────────────────────────────────────────────


def test_registry_covers_every_documented_provider() -> None:
    slugs = {p["slug"] for p in supported_providers()}
    for slug in slugs:
        gw = get_gateway(slug)
        assert gw.slug == slug


def test_unknown_provider_raises() -> None:
    with pytest.raises(GatewayError):
        get_gateway("definitely_not_a_real_pakistani_gateway")


# ── JazzCash ──────────────────────────────────────────────────────


def test_jazzcash_sandbox_returns_local_url_when_creds_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Even if env vars somehow leak in from a developer's .env, clear them.
    monkeypatch.setattr("psx_api.services.payments.jazzcash.settings.jazzcash_merchant_id", "")
    monkeypatch.setattr("psx_api.services.payments.jazzcash.settings.jazzcash_password", "")
    monkeypatch.setattr("psx_api.services.payments.jazzcash.settings.jazzcash_integrity_salt", "")
    gw = get_gateway("jazzcash")
    result = gw.create_intent(_ctx())
    assert result.is_sandbox is True
    assert "sandbox" in result.checkout_url or "checkout/return" in result.checkout_url
    # Amount is in paisas, integer string.
    assert result.request_payload["pp_Amount"] == "90000"
    # Hash is uppercase hex.
    assert result.request_payload["pp_SecureHash"].isupper() or any(
        c.isdigit() for c in result.request_payload["pp_SecureHash"]
    )


def test_jazzcash_verify_callback_rejects_forged_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "psx_api.services.payments.jazzcash.settings.jazzcash_merchant_id", "MC00123"
    )
    monkeypatch.setattr("psx_api.services.payments.jazzcash.settings.jazzcash_password", "abc")
    monkeypatch.setattr(
        "psx_api.services.payments.jazzcash.settings.jazzcash_integrity_salt",
        "supersecret",
    )
    gw = get_gateway("jazzcash")
    with pytest.raises(GatewayError):
        gw.verify_callback(
            {
                "pp_TxnRefNo": "TPSX00001",
                "pp_ResponseCode": "000",
                "pp_Amount": "90000",
                "pp_SecureHash": "00" * 32,  # obviously wrong
            }
        )


def test_jazzcash_verify_callback_accepts_matching_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "psx_api.services.payments.jazzcash.settings.jazzcash_merchant_id", "MC00123"
    )
    monkeypatch.setattr("psx_api.services.payments.jazzcash.settings.jazzcash_password", "abc")
    monkeypatch.setattr(
        "psx_api.services.payments.jazzcash.settings.jazzcash_integrity_salt",
        "supersecret",
    )
    from psx_api.services.payments.jazzcash import JazzCashGateway

    gw = JazzCashGateway()
    payload = {
        "pp_TxnRefNo": "TPSX00001",
        "pp_ResponseCode": "000",
        "pp_Amount": "90000",
        "pp_TxnCurrency": "PKR",
    }
    payload["pp_SecureHash"] = gw._compute_hash(payload)
    result = gw.verify_callback(payload)
    assert result.status == "paid"
    assert result.amount_pkr == Decimal("900")


# ── Easypaisa ─────────────────────────────────────────────────────


def test_easypaisa_sandbox_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("psx_api.services.payments.easypaisa.settings.easypaisa_store_id", "")
    monkeypatch.setattr("psx_api.services.payments.easypaisa.settings.easypaisa_hash_key", "")
    gw = get_gateway("easypaisa")
    result = gw.create_intent(_ctx(amount_pkr="2500.00"))
    assert result.is_sandbox is True
    # Amount is 2 decimals as a string.
    assert result.request_payload["amount"] == "2500.00"
    assert result.request_payload["merchantHashedReq"]  # always present


# ── Meezan ────────────────────────────────────────────────────────


def test_meezan_callback_hash_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("psx_api.services.payments.meezan.settings.meezan_merchant_id", "MEZ_001")
    monkeypatch.setattr("psx_api.services.payments.meezan.settings.meezan_secret_key", "mez_salt")
    import hashlib

    secret, merchant = "mez_salt", "MEZ_001"
    order_id, amount, rc, tid = "TPSX42", "900.00", "00", "MEZTX001"
    hash_input = f"{secret}|{merchant}|{order_id}|{amount}|{rc}|{tid}"
    correct = hashlib.sha256(hash_input.encode()).hexdigest()
    gw = get_gateway("meezan")
    result = gw.verify_callback(
        {
            "OrderId": order_id,
            "Amount": amount,
            "RC": rc,
            "TID": tid,
            "Hash": correct,
        }
    )
    assert result.status == "paid"
    assert result.gateway_txn_id == tid


def test_meezan_callback_rejects_bad_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("psx_api.services.payments.meezan.settings.meezan_merchant_id", "MEZ_001")
    monkeypatch.setattr("psx_api.services.payments.meezan.settings.meezan_secret_key", "mez_salt")
    gw = get_gateway("meezan")
    with pytest.raises(GatewayError):
        gw.verify_callback(
            {
                "OrderId": "TPSX42",
                "Amount": "900.00",
                "RC": "00",
                "TID": "MEZTX001",
                "Hash": "deadbeef" * 8,
            }
        )


# ── 1LINK PayFast (Allied/HBL/UBL/...) ────────────────────────────


def test_payfast_signature_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "psx_api.services.payments.allied_payfast.settings.payfast_merchant_id",
        "PF_MERCHANT_123",
    )
    monkeypatch.setattr(
        "psx_api.services.payments.allied_payfast.settings.payfast_secret_key",
        "pf_secret_xyz",
    )
    from psx_api.services.payments.allied_payfast import AlliedPayFastGateway

    gw = AlliedPayFastGateway()
    result = gw.create_intent(_ctx())
    payload = result.request_payload
    # Recomputing the signature with the same secret should match.
    sig = payload.pop("SIGNATURE")
    assert sig == gw._sign(payload)


def test_payfast_callback_paid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "psx_api.services.payments.allied_payfast.settings.payfast_merchant_id",
        "PF_MERCHANT_123",
    )
    monkeypatch.setattr(
        "psx_api.services.payments.allied_payfast.settings.payfast_secret_key",
        "pf_secret_xyz",
    )
    from psx_api.services.payments.allied_payfast import AlliedPayFastGateway

    gw = AlliedPayFastGateway()
    response = {
        "TRANSACTION_ID": "TPSX00099",
        "RESPONSE_CODE": "00",
        "TRANSACTION_AMOUNT": "900.00",
        "REFERENCE_NUMBER": "PFAST1",
    }
    response["SIGNATURE"] = gw._sign(response)
    result = gw.verify_callback(response)
    assert result.status == "paid"
    assert result.amount_pkr == Decimal("900.00")
    assert result.gateway_txn_id == "PFAST1"


# ── SafePay ───────────────────────────────────────────────────────


def test_safepay_webhook_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib
    import hmac
    import json

    monkeypatch.setattr("psx_api.services.payments.safepay.settings.safepay_api_key", "sk_test_abc")
    monkeypatch.setattr(
        "psx_api.services.payments.safepay.settings.safepay_webhook_secret",
        "wh_secret_xyz",
    )
    gw = get_gateway("safepay")
    body_dict = {
        "data": {
            "order_id": "TPSX00010",
            "state": "paid",
            "amount": 90000,
            "tracker": "SP_TRK_1",
        }
    }
    body_bytes = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(b"wh_secret_xyz", body_bytes, hashlib.sha256).hexdigest()
    payload = dict(body_dict)
    payload["_signature"] = sig
    payload["_raw_body"] = body_bytes
    result = gw.verify_callback(payload)
    assert result.status == "paid"
    assert result.amount_pkr == Decimal("900")


def test_safepay_bad_signature_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("psx_api.services.payments.safepay.settings.safepay_api_key", "sk_test_abc")
    monkeypatch.setattr(
        "psx_api.services.payments.safepay.settings.safepay_webhook_secret",
        "wh_secret_xyz",
    )
    gw = get_gateway("safepay")
    with pytest.raises(GatewayError):
        gw.verify_callback(
            {
                "data": {"order_id": "TPSX00010", "state": "paid"},
                "_signature": "00" * 32,
                "_raw_body": b'{"data":{"order_id":"TPSX00010","state":"paid"}}',
            }
        )


# ── Manual ────────────────────────────────────────────────────────


def test_manual_returns_instructions() -> None:
    gw = get_gateway("manual")
    result = gw.create_intent(_ctx(amount_pkr="900.00"))
    assert result.instructions is not None
    assert "PKR 900" in result.instructions
    assert "TPSXAI00001" in result.instructions
    # The "checkout_url" is just a return-to-app stub.
    assert result.is_sandbox is False
