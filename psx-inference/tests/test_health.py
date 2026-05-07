import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["models_loaded"] == 0


@pytest.mark.asyncio
async def test_accuracy_threshold_is_above_random(client: AsyncClient) -> None:
    from psx_inference.config import settings
    # Threshold must be strictly above 50% — below that we'd be worse than a coin flip
    assert settings.model_accuracy_threshold > 0.50
