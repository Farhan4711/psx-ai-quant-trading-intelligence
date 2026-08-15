"""News + sentiment endpoints (Phase 3 Steps 49–52)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.schemas.news import NewsPulseResponse
from psx_api.services.news_service import NewsService

router = APIRouter(prefix="/api/v1", tags=["news"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/securities/{symbol}/news/pulse", response_model=NewsPulseResponse)
async def get_pulse(symbol: str, db: DbDep) -> NewsPulseResponse:
    service = NewsService(db)
    data = await service.pulse(symbol.upper())
    return NewsPulseResponse(**data)


@router.get("/securities/{symbol}/news")
async def get_articles(symbol: str, db: DbDep, limit: int = 20) -> list[dict[str, Any]]:
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit must be 1..100")
    service = NewsService(db)
    return await service.articles_for_symbol(symbol.upper(), limit=limit)
