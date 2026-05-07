import pytest
from httpx import ASGITransport, AsyncClient

from psx_api.main import app


@pytest.fixture
async def health_client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_returns_ok(health_client: AsyncClient) -> None:
    response = await health_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_response_shape(health_client: AsyncClient) -> None:
    response = await health_client.get("/health")
    data = response.json()
    assert set(data.keys()) == {"status", "version"}
