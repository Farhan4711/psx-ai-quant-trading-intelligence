"""Backtest endpoints (Phase 2 Steps 37–40)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.backtest.strategies import list_strategies
from psx_api.database import get_db
from psx_api.schemas.backtest import BacktestRequest, BacktestResult, StrategyMeta
from psx_api.services.backtest_service import BacktestError, BacktestService

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/strategies", response_model=list[StrategyMeta])
async def list_available_strategies() -> list[StrategyMeta]:
    return [StrategyMeta(**s) for s in list_strategies()]


@router.post("", response_model=BacktestResult)
async def run_backtest(req: BacktestRequest, db: DbDep) -> BacktestResult:
    service = BacktestService(db)
    try:
        return await service.run(req)
    except BacktestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
