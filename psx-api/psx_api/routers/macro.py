"""Macro indicator endpoints (Phase 2 Steps 47–48)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.services.macro_service import SUPPORTED_INDICATORS, MacroService

router = APIRouter(prefix="/api/v1/macro", tags=["macro"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/indicators")
async def list_indicators() -> list[dict[str, Any]]:
    return SUPPORTED_INDICATORS


@router.get("/series/{indicator}")
async def get_series(
    indicator: str,
    db: DbDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    valid = {i["key"] for i in SUPPORTED_INDICATORS}
    if indicator not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown indicator '{indicator}'. Valid: {sorted(valid)}",
        )
    service = MacroService(db)
    return await service.series(indicator, date_from=date_from, date_to=date_to)
