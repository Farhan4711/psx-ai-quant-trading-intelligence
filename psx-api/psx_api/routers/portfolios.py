"""
Portfolio + Transaction REST endpoints.

  GET    /api/v1/portfolios
  POST   /api/v1/portfolios
  GET    /api/v1/portfolios/{id}
  PATCH  /api/v1/portfolios/{id}
  DELETE /api/v1/portfolios/{id}

  GET    /api/v1/portfolios/{id}/transactions
  POST   /api/v1/portfolios/{id}/transactions/preview
  POST   /api/v1/portfolios/{id}/transactions
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.portfolios import (
    PortfolioCreate,
    PortfolioResponse,
    PortfolioSummary,
    PortfolioUpdate,
    TransactionCreate,
    TransactionPreview,
    TransactionResponse,
)
from psx_api.services.auth_service import AuthService
from psx_api.services.portfolio_service import PortfolioError, PortfolioService
from psx_api.services.portfolio_summary_service import PortfolioSummaryService
from psx_api.services.transaction_service import TransactionError, TransactionService

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])

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


# ── Portfolios ──────────────────────────────────────────────────────────


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(db: DbDep, current_user: CurrentUser) -> list[PortfolioResponse]:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = PortfolioService(db)
    portfolios = await service.list_for_user(user.id)
    # Auto-create a default portfolio on first load so the trade-entry UI
    # always has somewhere to write to
    if not portfolios:
        default = await service.get_or_create_default(user.id)
        portfolios = [default]
    return [PortfolioResponse.model_validate(p) for p in portfolios]


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate, db: DbDep, current_user: CurrentUser
) -> PortfolioResponse:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = PortfolioService(db)
    try:
        portfolio = await service.create(user.id, body)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return PortfolioResponse.model_validate(portfolio)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: str, db: DbDep, current_user: CurrentUser
) -> PortfolioResponse:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = PortfolioService(db)
    try:
        portfolio = await service.get(user.id, portfolio_id)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return PortfolioResponse.model_validate(portfolio)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: str, body: PortfolioUpdate, db: DbDep, current_user: CurrentUser
) -> PortfolioResponse:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = PortfolioService(db)
    try:
        portfolio = await service.update(user.id, portfolio_id, body)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return PortfolioResponse.model_validate(portfolio)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str, db: DbDep, current_user: CurrentUser
) -> None:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    service = PortfolioService(db)
    try:
        await service.delete(user.id, portfolio_id)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    portfolio_id: str, db: DbDep, current_user: CurrentUser
) -> PortfolioSummary:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    portfolio_service = PortfolioService(db)
    try:
        portfolio = await portfolio_service.get(user.id, portfolio_id)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    summary_service = PortfolioSummaryService(db)
    data = await summary_service.summary(portfolio, is_filer=user.is_filer)
    return PortfolioSummary.model_validate(data)


# ── Transactions ───────────────────────────────────────────────────────


@router.get(
    "/{portfolio_id}/transactions", response_model=list[TransactionResponse]
)
async def list_transactions(
    portfolio_id: str, db: DbDep, current_user: CurrentUser, limit: int = 200
) -> list[TransactionResponse]:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    portfolio_service = PortfolioService(db)
    try:
        portfolio = await portfolio_service.get(user.id, portfolio_id)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    txn_service = TransactionService(db)
    txns = await txn_service.list_for_portfolio(portfolio, limit=limit)
    return [TransactionResponse.model_validate(t) for t in txns]


@router.post(
    "/{portfolio_id}/transactions/preview", response_model=TransactionPreview
)
async def preview_transaction(
    portfolio_id: str,
    body: TransactionCreate,
    db: DbDep,
    current_user: CurrentUser,
) -> TransactionPreview:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    portfolio_service = PortfolioService(db)
    try:
        portfolio = await portfolio_service.get(user.id, portfolio_id)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    txn_service = TransactionService(db)
    try:
        return await txn_service.preview(portfolio, body, user)
    except TransactionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    portfolio_id: str,
    body: TransactionCreate,
    db: DbDep,
    current_user: CurrentUser,
) -> TransactionResponse:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    portfolio_service = PortfolioService(db)
    try:
        portfolio = await portfolio_service.get(user.id, portfolio_id)
    except PortfolioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    txn_service = TransactionService(db)
    try:
        txn, _ = await txn_service.create(portfolio, body, user)
    except TransactionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return TransactionResponse.model_validate(txn)
