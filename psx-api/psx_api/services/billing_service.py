"""
Billing service — subscription plans + user subscriptions + payment intents.

The paid path now actually does something: it creates a PaymentIntent
row, hands it to the chosen Pakistani gateway (JazzCash/Easypaisa/
Meezan/PayFast/SafePay/NayaPay/manual), and returns the checkout URL
the frontend should redirect to. On callback, `confirm_payment` flips
the intent to `paid` and creates/extends the UserSubscription.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.config import settings
from psx_api.models.billing import SubscriptionPlan, UserSubscription
from psx_api.models.payments import PaymentIntent
from psx_api.services.payments import (
    CheckoutContext,
    GatewayError,
    get_gateway,
)
from psx_api.timezone import today_pkt


class BillingError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


_PROVIDERS_REQUIRING_CHECKOUT = {
    "jazzcash",
    "easypaisa",
    "meezan",
    "allied_payfast",
    "safepay",
    "nayapay",
}


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Plans (public) ────────────────────────────────────────────

    async def list_plans(self) -> list[SubscriptionPlan]:
        rows = (
            (
                await self._db.execute(
                    select(SubscriptionPlan)
                    .where(SubscriptionPlan.is_active.is_(True))
                    .order_by(SubscriptionPlan.display_order)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def get_plan_by_slug(self, slug: str) -> SubscriptionPlan | None:
        return (
            await self._db.execute(select(SubscriptionPlan).where(SubscriptionPlan.slug == slug))
        ).scalar_one_or_none()

    # ── Subscriptions (per-user) ──────────────────────────────────

    async def current_subscription(
        self, user_id: str
    ) -> tuple[UserSubscription | None, SubscriptionPlan | None]:
        result = await self._db.execute(
            select(UserSubscription, SubscriptionPlan)
            .join(SubscriptionPlan, SubscriptionPlan.id == UserSubscription.plan_id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.status.in_(("active", "trialing")),
            )
            .order_by(desc(UserSubscription.created_at))
            .limit(1)
        )
        row = result.first()
        if row is None:
            free_plan = await self.get_plan_by_slug("free")
            return None, free_plan
        sub, plan = row
        return sub, plan

    async def subscribe_free(self, user_id: str) -> UserSubscription:
        plan = await self.get_plan_by_slug("free")
        if not plan:
            raise BillingError("Free plan not configured.", status_code=500)

        existing_rows = (
            (
                await self._db.execute(
                    select(UserSubscription).where(
                        UserSubscription.user_id == user_id,
                        UserSubscription.status.in_(("active", "trialing")),
                    )
                )
            )
            .scalars()
            .all()
        )
        for existing in existing_rows:
            existing.status = "canceled"
            existing.cancel_at_period_end = True
        if existing_rows:
            await self._db.flush()

        today = today_pkt()
        sub = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            status="active",
            provider=None,
            period_start=today,
            period_end=today + timedelta(days=3650),
        )
        self._db.add(sub)
        await self._db.flush()
        await self._db.refresh(sub)
        return sub

    # ── Paid subscriptions via Pakistani gateways ────────────────

    async def begin_paid_subscription(
        self,
        *,
        user_id: str,
        user_email: str,
        user_name: str | None,
        user_phone: str | None,
        plan_slug: str,
        provider: str,
        billing_cycle: str = "monthly",
    ) -> dict[str, Any]:
        """
        Create a PaymentIntent + dispatch to the chosen gateway.

        Returns a dict the frontend can act on:
          {
            "intent_id": "...",
            "provider": "jazzcash",
            "checkout_url": "https://...",
            "is_sandbox": false,
            "instructions": null,        # populated for "manual"
            "request_payload": {...},    # for redirect gateways: form fields
                                         # the frontend hidden-form-submits
            "amount_pkr": "900.00",
            "expires_at": "2026-05-15T15:00:00+05:00"
          }
        """
        if billing_cycle not in ("monthly", "annual"):
            raise BillingError(
                f"Unknown billing_cycle '{billing_cycle}' — expected monthly or annual."
            )

        plan = await self.get_plan_by_slug(plan_slug)
        if not plan:
            raise BillingError(f"Unknown plan '{plan_slug}'.", status_code=404)
        if plan.slug == "free":
            raise BillingError(
                "Free plan doesn't go through checkout — use /api/v1/billing/subscribe-free."
            )

        amount = (
            plan.price_pkr_annual or Decimal(plan.price_pkr_monthly) * Decimal(12)
            if billing_cycle == "annual"
            else plan.price_pkr_monthly
        )
        if amount is None or amount <= 0:
            raise BillingError("Plan has no price configured.", status_code=500)

        try:
            gateway = get_gateway(provider)
        except GatewayError as exc:
            raise BillingError(str(exc), status_code=400) from exc

        # Reference: T + 8 hex chars (JazzCash limit is 20 chars; this is 9)
        # Prefix `T` so JazzCash accepts it; the other gateways are fine with
        # arbitrary alphanumerics.
        merchant_ref = "T" + secrets.token_hex(8).upper()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        callback_url = (
            settings.payments_base_url.rstrip("/") + f"/api/v1/billing/callback/{provider}"
        )
        return_url = settings.payments_return_url.rstrip("/") + f"?ref={merchant_ref}"

        ctx = CheckoutContext(
            merchant_txn_ref=merchant_ref,
            amount_pkr=Decimal(amount),
            description=f"PSX AI {plan.name} ({billing_cycle})",
            customer_email=user_email,
            customer_name=user_name,
            customer_phone=user_phone,
            return_url=return_url,
            callback_url=callback_url,
            expires_at_unix=int(expires_at.timestamp()),
        )

        try:
            result = gateway.create_intent(ctx)
        except GatewayError as exc:
            raise BillingError(
                f"{provider} checkout failed: {exc}",
                status_code=exc.status_code,
            ) from exc

        intent = PaymentIntent(
            user_id=user_id,
            plan_id=plan.id,
            provider=provider,
            billing_cycle=billing_cycle,
            amount_pkr=Decimal(amount),
            status="redirected" if provider in _PROVIDERS_REQUIRING_CHECKOUT else "pending",
            merchant_txn_ref=merchant_ref,
            gateway_txn_id=result.gateway_txn_id,
            request_payload=result.request_payload,
            checkout_url=result.checkout_url,
            expires_at=expires_at,
        )
        self._db.add(intent)
        await self._db.flush()
        await self._db.refresh(intent)

        return {
            "intent_id": intent.id,
            "provider": provider,
            "checkout_url": result.checkout_url,
            "is_sandbox": result.is_sandbox,
            "instructions": result.instructions,
            "request_payload": result.request_payload,
            "amount_pkr": str(intent.amount_pkr),
            "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
        }

    async def confirm_payment(
        self,
        *,
        provider: str,
        payload: dict[str, Any],
    ) -> PaymentIntent:
        """
        Verify a gateway callback and, on success, activate the
        UserSubscription. Idempotent: re-running on an already-paid
        intent is a no-op.
        """
        try:
            gateway = get_gateway(provider)
        except GatewayError as exc:
            raise BillingError(str(exc), status_code=400) from exc

        try:
            result = gateway.verify_callback(payload)
        except GatewayError as exc:
            raise BillingError(str(exc), status_code=exc.status_code) from exc

        intent = (
            await self._db.execute(
                select(PaymentIntent).where(
                    PaymentIntent.merchant_txn_ref == result.merchant_txn_ref,
                    PaymentIntent.provider == provider,
                )
            )
        ).scalar_one_or_none()

        if not intent:
            raise BillingError(
                f"No matching payment intent for ref {result.merchant_txn_ref}.",
                status_code=404,
            )

        # Idempotent: a duplicate webhook for an already-paid intent
        # just records the second response_payload and returns.
        intent.response_payload = result.raw_payload
        intent.returned_at = datetime.now(UTC)
        intent.gateway_txn_id = result.gateway_txn_id or intent.gateway_txn_id

        if intent.status == "paid":
            return intent

        if result.status == "paid":
            # Sanity-check amount: gateway should echo what we billed.
            if result.amount_pkr is not None and abs(
                Decimal(result.amount_pkr) - Decimal(intent.amount_pkr)
            ) > Decimal("0.01"):
                intent.status = "failed"
                intent.failure_reason = (
                    f"Amount mismatch: expected {intent.amount_pkr}, "
                    f"gateway sent {result.amount_pkr}"
                )
                return intent

            intent.status = "paid"
            await self._activate_subscription(intent)
        elif result.status == "canceled":
            intent.status = "canceled"
            intent.failure_reason = result.failure_reason
        elif result.status == "pending":
            intent.status = "redirected"
        else:
            intent.status = "failed"
            intent.failure_reason = result.failure_reason

        await self._db.flush()
        return intent

    async def _activate_subscription(self, intent: PaymentIntent) -> None:
        # Cancel any other active subscription first (downgrade or
        # provider-switch case).
        existing = (
            (
                await self._db.execute(
                    select(UserSubscription).where(
                        UserSubscription.user_id == intent.user_id,
                        UserSubscription.status.in_(("active", "trialing")),
                    )
                )
            )
            .scalars()
            .all()
        )
        for sub in existing:
            sub.status = "canceled"
            sub.cancel_at_period_end = True

        today = today_pkt()
        period_end = today + (
            timedelta(days=365) if intent.billing_cycle == "annual" else timedelta(days=30)
        )

        sub = UserSubscription(
            user_id=intent.user_id,
            plan_id=intent.plan_id,
            status="active",
            provider=intent.provider,
            provider_subscription_id=intent.gateway_txn_id or intent.merchant_txn_ref,
            period_start=today,
            period_end=period_end,
        )
        self._db.add(sub)
        await self._db.flush()
