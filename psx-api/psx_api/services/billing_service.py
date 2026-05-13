"""
Billing service — subscription plans + user subscriptions.

Phase 5 v1 ships the **read paths** and a stub subscribe/cancel that
records the row but doesn't hit a payment provider. The provider field
on user_subscriptions is intentionally string-typed so we can plug in
Stripe / JazzCash / Easypaisa / SafePay without schema migrations when
the time comes.

For the free plan, subscribing is local-only — no provider interaction.
Paid plans return a 501 Not Implemented so the UI shows "Payment
integration coming soon" rather than silently activating a paid plan.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.billing import SubscriptionPlan, UserSubscription


class BillingError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Plans (public) ────────────────────────────────────────────

    async def list_plans(self) -> list[SubscriptionPlan]:
        rows = (
            await self._db.execute(
                select(SubscriptionPlan)
                .where(SubscriptionPlan.is_active.is_(True))
                .order_by(SubscriptionPlan.display_order)
            )
        ).scalars().all()
        return list(rows)

    async def get_plan_by_slug(self, slug: str) -> SubscriptionPlan | None:
        return (
            await self._db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.slug == slug)
            )
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
            # No subscription record → treat as Free plan
            free_plan = await self.get_plan_by_slug("free")
            return None, free_plan
        sub, plan = row
        return sub, plan

    async def subscribe_free(self, user_id: str) -> UserSubscription:
        """
        Activate the free plan locally — no payment provider involved.
        Cancels any other active subscription first.
        """
        plan = await self.get_plan_by_slug("free")
        if not plan:
            raise BillingError("Free plan not configured.", status_code=500)

        # End any existing active subscription
        existing_rows = (
            await self._db.execute(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status.in_(("active", "trialing")),
                )
            )
        ).scalars().all()
        for existing in existing_rows:
            existing.status = "canceled"
            existing.cancel_at_period_end = True
        if existing_rows:
            await self._db.flush()

        today = date.today()
        sub = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            status="active",
            provider=None,
            period_start=today,
            period_end=today + timedelta(days=3650),  # essentially forever
        )
        self._db.add(sub)
        await self._db.flush()
        await self._db.refresh(sub)
        return sub

    async def begin_paid_subscription(
        self, user_id: str, plan_slug: str
    ) -> dict:
        """
        Stub for paid-plan signup. Returns a payload the frontend uses
        to redirect to a checkout flow. Until a real provider is wired
        in, this returns `provider: "manual"` and a friendly message
        instead of a checkout URL.
        """
        plan = await self.get_plan_by_slug(plan_slug)
        if not plan:
            raise BillingError(f"Unknown plan '{plan_slug}'.", status_code=404)
        if plan.slug == "free":
            raise BillingError(
                "Free plan doesn't go through checkout — use /api/v1/billing/subscribe-free."
            )

        # No payment provider wired up yet — return a deferred-checkout
        # response so the UI can show "we'll email you when payment is
        # ready" rather than failing.
        return {
            "provider": "manual",
            "plan_slug": plan.slug,
            "amount_pkr_monthly": str(plan.price_pkr_monthly),
            "checkout_url": None,
            "message": (
                "Paid plans aren't wired to a payment provider yet. "
                "Email us at hello@psxai.example and we'll activate it "
                "manually for early users."
            ),
        }
