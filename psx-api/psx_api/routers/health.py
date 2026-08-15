from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from psx_api.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/health/sentry-check")
async def sentry_check() -> None:
    """
    Deliberately raises so Sentry's exception capture path can be verified
    end-to-end. Disabled in production unless explicitly opted-in via env.
    """
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    raise RuntimeError("Sentry test exception — health/sentry-check")
