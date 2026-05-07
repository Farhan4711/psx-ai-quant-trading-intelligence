from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: int


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    # Phase 2: report actual loaded model count
    return HealthResponse(status="ok", version="0.1.0", models_loaded=0)
