from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.securities import (
    AnnouncementsListResponse,
    FundamentalsResponse,
    IndexPerformance,
    OhlcvListResponse,
    QuotesResponse,
    SecuritiesListResponse,
    SecurityResponse,
)
from psx_api.services.indicator_service import SUPPORTED, IndicatorService
from psx_api.services.securities_service import SecuritiesService

router = APIRouter(prefix="/api/v1", tags=["securities"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def _service(db: DbDep, redis: RedisDep) -> SecuritiesService:
    return SecuritiesService(db, redis)


ServiceDep = Annotated[SecuritiesService, Depends(_service)]


@router.get("/securities", response_model=SecuritiesListResponse)
async def list_securities(
    service: ServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    sector: str | None = None,
    kmi_only: bool = False,
    kse100_only: bool = False,
    search: str | None = None,
) -> SecuritiesListResponse:
    return await service.list_securities(
        page=page,
        page_size=page_size,
        sector=sector,
        kmi_only=kmi_only,
        kse100_only=kse100_only,
        search=search,
    )


@router.get("/securities/{symbol}", response_model=SecurityResponse)
async def get_security(symbol: str, service: ServiceDep) -> SecurityResponse:
    security = await service.get_security(symbol)
    if not security:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Security '{symbol.upper()}' not found."
        )
    return security


@router.get("/securities/{symbol}/ohlcv", response_model=OhlcvListResponse)
async def get_ohlcv(
    symbol: str,
    service: ServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 252,
    adjusted: bool = True,
) -> OhlcvListResponse:
    if not await service.get_security(symbol):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Security '{symbol.upper()}' not found."
        )
    return await service.get_ohlcv(
        symbol, date_from=date_from, date_to=date_to, limit=limit, adjusted=adjusted
    )


@router.get("/securities/{symbol}/fundamentals", response_model=FundamentalsResponse)
async def get_fundamentals(symbol: str, service: ServiceDep) -> FundamentalsResponse:
    fundamentals = await service.get_fundamentals(symbol)
    if not fundamentals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Security '{symbol.upper()}' not found."
        )
    return fundamentals


@router.get("/securities/{symbol}/announcements", response_model=AnnouncementsListResponse)
async def get_announcements(
    symbol: str,
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnnouncementsListResponse:
    if not await service.get_security(symbol):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Security '{symbol.upper()}' not found."
        )
    return await service.get_announcements(symbol, limit=limit)


@router.get("/quotes", response_model=QuotesResponse)
async def get_quotes(
    service: ServiceDep,
    symbols: Annotated[str, Query(description="Comma-separated symbols")],
) -> QuotesResponse:
    parts = [s.strip() for s in symbols.split(",") if s.strip()]
    if not parts:
        return QuotesResponse(items=[])
    if len(parts) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At most 100 symbols per request.",
        )
    return await service.get_quotes(parts)


@router.get("/sectors", response_model=list[str])
async def list_sectors(service: ServiceDep) -> list[str]:
    return await service.list_sectors()


@router.get("/indices", response_model=list[IndexPerformance])
async def get_indices(service: ServiceDep) -> list[IndexPerformance]:
    return await service.get_indices()


@router.get("/indicators/list")
async def list_supported_indicators() -> list[dict[str, Any]]:
    return SUPPORTED


@router.get("/securities/{symbol}/indicators/{indicator}")
async def compute_indicator(
    symbol: str,
    indicator: str,
    db: DbDep,
    redis: RedisDep,
) -> dict[str, Any]:
    valid = {s["key"] for s in SUPPORTED}
    if indicator not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown indicator '{indicator}'. Valid: {sorted(valid)}",
        )
    service = IndicatorService(db, redis)
    return await service.compute_indicator(symbol.upper(), indicator)  # type: ignore[arg-type]
