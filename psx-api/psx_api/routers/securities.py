from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.schemas.securities import (
    OhlcvListResponse,
    SecuritiesListResponse,
    SecurityResponse,
)
from psx_api.services.securities_service import SecuritiesService

router = APIRouter(prefix="/api/v1", tags=["securities"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _service(db: DbDep) -> SecuritiesService:
    return SecuritiesService(db)


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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security '{symbol.upper()}' not found.",
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
    security = await service.get_security(symbol)
    if not security:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security '{symbol.upper()}' not found.",
        )
    return await service.get_ohlcv(
        symbol,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        adjusted=adjusted,
    )


@router.get("/sectors", response_model=list[str])
async def list_sectors(service: ServiceDep) -> list[str]:
    return await service.list_sectors()
