"""Suspicious-day pump/dump alert endpoints (Phase 3 Steps 54–57)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.alerts import StockSuspiciousState, SuspiciousDayResponse
from psx_api.services.alert_service import AlertService
from psx_api.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1", tags=["alerts"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]  # type: ignore[type-arg]


async def _current_user(
    db: DbDep,
    redis: RedisDep,
    psx_session: Annotated[str | None, Cookie()] = None,
) -> object:
    if not psx_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    auth = AuthService(db, redis)
    user = await auth.get_session_user(psx_session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


CurrentUser = Annotated[object, Depends(_current_user)]


@router.get(
    "/securities/{symbol}/suspicious-state", response_model=StockSuspiciousState
)
async def get_suspicious_state(symbol: str, db: DbDep) -> StockSuspiciousState:
    """Latest suspicious-day flag for the stock detail page banner."""
    service = AlertService(db)
    latest = await service.latest_for_symbol(symbol.upper())
    return StockSuspiciousState(
        has_active_alert=latest is not None,
        latest=SuspiciousDayResponse.model_validate(latest) if latest else None,
    )


@router.get("/alerts", response_model=list[SuspiciousDayResponse])
async def list_alerts_for_user(
    db: DbDep, current_user: CurrentUser, limit: int = 50
) -> list[SuspiciousDayResponse]:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = AlertService(db)
    rows = await service.for_user(user.id, limit=limit)
    return [SuspiciousDayResponse.model_validate(r) for r in rows]


@router.post(
    "/securities/{symbol}/suspicious-evaluate", response_model=SuspiciousDayResponse | None
)
async def evaluate_today(
    symbol: str, db: DbDep, current_user: CurrentUser
) -> SuspiciousDayResponse | None:
    """
    Run the pump/dump pipeline on demand for `symbol` against the latest
    OHLCV bar. Daily worker calls this for every active stock; UI exposes
    it for power users.
    """
    service = AlertService(db)
    row = await service.evaluate_today(symbol.upper())
    if row is None:
        return None
    return SuspiciousDayResponse.model_validate(row)
