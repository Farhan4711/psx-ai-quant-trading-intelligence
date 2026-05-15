"""Subscription plans + Pakistani payment-gateway checkout."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.models.billing import SubscriptionPlan
from psx_api.models.payments import PaymentIntent
from psx_api.redis_client import get_redis
from psx_api.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    CurrentSubscriptionResponse,
    PaymentIntentStatus,
    PaymentMethodOption,
    SubscriptionPlanResponse,
)
from psx_api.services.auth_service import AuthService
from psx_api.services.billing_service import BillingError, BillingService
from psx_api.services.payments import supported_providers

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]  # type: ignore[type-arg]


async def _current_user(
    db: DbDep,
    redis: RedisDep,
    psx_session: Annotated[str | None, Cookie()] = None,
) -> object:
    if not psx_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    auth = AuthService(db, redis)
    user = await auth.get_session_user(psx_session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )
    return user


CurrentUser = Annotated[object, Depends(_current_user)]


# ── Public ────────────────────────────────────────────────────────


@router.get("/plans", response_model=list[SubscriptionPlanResponse])
async def list_plans(db: DbDep) -> list[SubscriptionPlanResponse]:
    service = BillingService(db)
    plans = await service.list_plans()
    return [SubscriptionPlanResponse.model_validate(p) for p in plans]


@router.get("/payment-methods", response_model=list[PaymentMethodOption])
async def list_payment_methods() -> list[PaymentMethodOption]:
    """The "pay with…" picker on the checkout page."""
    return [PaymentMethodOption(**m) for m in supported_providers()]


# ── Authenticated ─────────────────────────────────────────────────


@router.get("/me", response_model=CurrentSubscriptionResponse)
async def my_subscription(
    db: DbDep, current_user: CurrentUser
) -> CurrentSubscriptionResponse:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = BillingService(db)
    sub, plan = await service.current_subscription(user.id)
    if not plan:
        raise HTTPException(status_code=500, detail="No plans configured.")
    return CurrentSubscriptionResponse(
        plan=SubscriptionPlanResponse.model_validate(plan),
        status=sub.status if sub else "implicit_free",
        period_start=sub.period_start if sub else None,
        period_end=sub.period_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
    )


@router.post("/subscribe-free", status_code=status.HTTP_201_CREATED)
async def subscribe_free(db: DbDep, current_user: CurrentUser) -> dict:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = BillingService(db)
    try:
        sub = await service.subscribe_free(user.id)
    except BillingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"id": sub.id, "plan": "free", "status": sub.status}


@router.post("/checkout", response_model=CheckoutResponse)
async def begin_checkout(
    payload: CheckoutRequest, db: DbDep, current_user: CurrentUser
) -> CheckoutResponse:
    """
    Start a paid-plan checkout against the chosen Pakistani gateway.

    The frontend should:
      - For redirect gateways (JazzCash/Easypaisa/Meezan/PayFast): build a
        hidden form with `request_payload` fields and POST it to
        `checkout_url`.
      - For API gateways (SafePay/NayaPay): do `window.location = checkout_url`.
      - For `manual`: render `instructions` inline and tell the user to
        email the receipt.
    """
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = BillingService(db)
    try:
        result = await service.begin_paid_subscription(
            user_id=user.id,
            user_email=user.email,
            user_name=getattr(user, "full_name", None),
            user_phone=getattr(user, "phone", None),
            plan_slug=payload.plan_slug,
            provider=payload.provider,
            billing_cycle=payload.billing_cycle,
        )
    except BillingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return CheckoutResponse(**result)


@router.get("/intent/{intent_id}", response_model=PaymentIntentStatus)
async def get_intent_status(
    intent_id: str, db: DbDep, current_user: CurrentUser
) -> PaymentIntentStatus:
    """The frontend polls this after a gateway return to know whether
    the webhook landed and the subscription activated."""
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]

    intent = (
        await db.execute(
            select(PaymentIntent, SubscriptionPlan)
            .join(SubscriptionPlan, SubscriptionPlan.id == PaymentIntent.plan_id)
            .where(PaymentIntent.id == intent_id)
        )
    ).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found.")
    pi, plan = intent
    if pi.user_id != user.id:
        # 404, not 403 — don't leak existence of someone else's intent.
        raise HTTPException(status_code=404, detail="Intent not found.")

    return PaymentIntentStatus(
        id=pi.id,
        provider=pi.provider,  # type: ignore[arg-type]
        status=pi.status,  # type: ignore[arg-type]
        amount_pkr=str(pi.amount_pkr),
        billing_cycle=pi.billing_cycle,  # type: ignore[arg-type]
        plan_slug=plan.slug,
        failure_reason=pi.failure_reason,
        created_at=pi.created_at,
        returned_at=pi.returned_at,
    )


# ── Gateway callbacks (no auth — verified by signature) ──────────


@router.post("/callback/{provider}", include_in_schema=False)
async def gateway_callback(
    provider: str, request: Request, db: DbDep
) -> dict:
    """
    Generic callback endpoint per provider. Accepts both
    `application/json` (SafePay/NayaPay webhook style) and
    `application/x-www-form-urlencoded` (JazzCash/Easypaisa/Meezan/
    PayFast redirect-back style).

    Signature verification lives inside each gateway's `verify_callback`.
    A forged callback fails there before we touch the DB.
    """
    content_type = request.headers.get("content-type", "")
    payload: dict
    raw_body = await request.body()
    if "application/json" in content_type:
        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body.")
        # Attach signature header + raw body for REST-style gateways.
        payload["_signature"] = (
            request.headers.get("x-sfpy-signature")
            or request.headers.get("x-np-signature")
            or ""
        )
        payload["_raw_body"] = raw_body
    else:
        form = await request.form()
        payload = {k: form.get(k) for k in form.keys()}

    service = BillingService(db)
    try:
        intent = await service.confirm_payment(provider=provider, payload=payload)
    except BillingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    # Gateways generally just need a 200 — we return the merchant ref
    # too so test harnesses can verify the flow.
    return {
        "ok": True,
        "intent_id": intent.id,
        "status": intent.status,
        "merchant_txn_ref": intent.merchant_txn_ref,
    }


@router.post("/sandbox-confirm/{intent_id}", include_in_schema=False)
async def sandbox_confirm(
    intent_id: str, db: DbDep, current_user: CurrentUser
) -> dict:
    """
    Dev-only convenience. When a gateway is in sandbox mode (no
    merchant creds set), the redirect lands on `/checkout/sandbox`
    on the frontend instead of a real gateway. That page POSTs here to
    simulate a successful callback so the rest of the flow works.

    Refuses in production unless the intent is explicitly sandbox-flagged
    in its request_payload — belt-and-braces guard against the endpoint
    being exposed live.
    """
    from psx_api.config import settings
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]

    intent = (
        await db.execute(
            select(PaymentIntent).where(PaymentIntent.id == intent_id)
        )
    ).scalar_one_or_none()
    if not intent or intent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Intent not found.")

    if settings.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="Sandbox confirmation disabled in production.",
        )

    service = BillingService(db)
    # Compose a synthetic "paid" payload that each gateway's
    # verify_callback will accept (in sandbox mode the signature check
    # is bypassed automatically when creds aren't configured).
    synthetic: dict = {
        "merchant_txn_ref": intent.merchant_txn_ref,
        "amount_pkr": str(intent.amount_pkr),
    }
    if intent.provider == "jazzcash":
        synthetic.update({
            "pp_TxnRefNo": intent.merchant_txn_ref,
            "pp_ResponseCode": "000",
            "pp_Amount": str(int(intent.amount_pkr * 100)),
            "pp_RetreivalReferenceNo": "SANDBOX_" + intent.merchant_txn_ref,
        })
    elif intent.provider == "easypaisa":
        synthetic.update({
            "orderRefNum": intent.merchant_txn_ref,
            "status": "0000",
            "paymentToken": "SANDBOX_" + intent.merchant_txn_ref,
            "amount": str(intent.amount_pkr),
        })
    elif intent.provider == "meezan":
        synthetic.update({
            "OrderId": intent.merchant_txn_ref,
            "RC": "00",
            "TID": "SANDBOX_" + intent.merchant_txn_ref,
            "Amount": str(intent.amount_pkr),
        })
    elif intent.provider == "allied_payfast":
        synthetic.update({
            "TRANSACTION_ID": intent.merchant_txn_ref,
            "RESPONSE_CODE": "00",
            "TRANSACTION_AMOUNT": str(intent.amount_pkr),
            "REFERENCE_NUMBER": "SANDBOX_" + intent.merchant_txn_ref,
        })
    elif intent.provider == "safepay":
        synthetic = {
            "data": {
                "order_id": intent.merchant_txn_ref,
                "state": "paid",
                "amount": int(intent.amount_pkr * 100),
                "tracker": "SANDBOX_" + intent.merchant_txn_ref,
            },
        }
    elif intent.provider == "nayapay":
        synthetic = {
            "merchant_reference": intent.merchant_txn_ref,
            "status": "completed",
            "amount_paisas": int(intent.amount_pkr * 100),
            "transaction_id": "SANDBOX_" + intent.merchant_txn_ref,
        }

    try:
        result = await service.confirm_payment(
            provider=intent.provider, payload=synthetic
        )
    except BillingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"ok": True, "intent_id": result.id, "status": result.status}
