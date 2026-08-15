from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.securities import WatchlistItemResponse, WatchlistReorderRequest
from psx_api.services.auth_service import AuthService
from psx_api.services.watchlist_service import WatchlistError, WatchlistService

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])

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


@router.get("", response_model=list[WatchlistItemResponse])
async def get_watchlist(db: DbDep, current_user: CurrentUser) -> list[WatchlistItemResponse]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = WatchlistService(db)
    return await service.get_watchlist(user.id)


@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: dict,  # type: ignore[type-arg]
    db: DbDep,
    current_user: CurrentUser,
) -> WatchlistItemResponse:
    from pydantic import BaseModel

    class AddBody(BaseModel):
        symbol: str
        note: str | None = None

    parsed = AddBody.model_validate(body)
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = WatchlistService(db)
    try:
        return await service.add(user.id, parsed.symbol, parsed.note)
    except WatchlistError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.put("/reorder", response_model=list[WatchlistItemResponse])
async def reorder_watchlist(
    body: WatchlistReorderRequest,
    db: DbDep,
    current_user: CurrentUser,
) -> list[WatchlistItemResponse]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = WatchlistService(db)
    try:
        return await service.reorder(user.id, body.symbols)
    except WatchlistError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def remove_from_watchlist(symbol: str, db: DbDep, current_user: CurrentUser) -> None:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = WatchlistService(db)
    try:
        await service.remove(user.id, symbol)
    except WatchlistError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
