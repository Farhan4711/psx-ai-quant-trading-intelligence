"""Subscription plans + billing endpoints (Phase 5 Step 72)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.billing import (
    CheckoutResponse,
    CurrentSubscriptionResponse,
    SubscriptionPlanResponse,
)
from psx_api.services.auth_service import AuthService
from psx_api.services.billing_service import BillingError, BillingService

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


@router.get("/plans", response_model=list[SubscriptionPlanResponse])
async def list_plans(db: DbDep) -> list[SubscriptionPlanResponse]:
    """Public — the pricing page hits this without authentication."""
    service = BillingService(db)
    plans = await service.list_plans()
    return [SubscriptionPlanResponse.model_validate(p) for p in plans]


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


@router.post("/subscribe/{plan_slug}", response_model=CheckoutResponse)
async def begin_paid_subscription(
    plan_slug: str, db: DbDep, current_user: CurrentUser
) -> CheckoutResponse:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = BillingService(db)
    try:
        return CheckoutResponse(**(await service.begin_paid_subscription(user.id, plan_slug)))
    except BillingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
