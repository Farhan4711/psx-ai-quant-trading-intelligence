"""Sector comparison + heatmap endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.services.sector_service import SectorService

router = APIRouter(prefix="/api/v1/sectors", tags=["sectors"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/heatmap")
async def heatmap(
    db: DbDep, sector: str | None = None
) -> list[dict]:
    return await SectorService(db).heatmap(sector)


@router.get("/{sector_name}/compare")
async def compare(
    sector_name: str,
    db: DbDep,
    symbols: Annotated[str, Query(description="Comma-separated symbols, 2–4")],
) -> dict:
    parts = [s.strip() for s in symbols.split(",") if s.strip()]
    if not (2 <= len(parts) <= 4):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compare 2–4 symbols at a time.",
        )
    return await SectorService(db).compare(sector_name, parts)
