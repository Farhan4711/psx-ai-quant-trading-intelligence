"""Prediction endpoint (Phase 2 Steps 41–46)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.services.prediction_service import PredictionError, PredictionService

router = APIRouter(prefix="/api/v1", tags=["predictions"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/securities/{symbol}/prediction")
async def get_prediction(symbol: str, db: DbDep, horizon_days: int = 1) -> dict:
    if horizon_days not in (1, 5):
        raise HTTPException(status_code=400, detail="horizon_days must be 1 or 5")
    service = PredictionService(db)
    try:
        return await service.predict(symbol, horizon_days=horizon_days)
    except PredictionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
