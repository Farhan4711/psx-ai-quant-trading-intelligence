"""Filer-vs-non-filer simulator endpoint (Phase 3 Step 58)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.services.auth_service import AuthService
from psx_api.services.tax_simulator_service import TaxSimulatorService

router = APIRouter(prefix="/api/v1/tax-simulator", tags=["tax-simulator"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


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


@router.get("")
async def simulate(
    db: DbDep,
    current_user: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = TaxSimulatorService(db)
    return await service.simulate(user.id, date_from=date_from, date_to=date_to)
