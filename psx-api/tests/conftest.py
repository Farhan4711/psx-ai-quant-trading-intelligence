from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.main import app
from psx_api.models.securities import Security
from psx_api.schemas.securities import OhlcvListResponse, SecuritiesListResponse, SecurityResponse


def _make_security(**kwargs: object) -> Security:
    defaults: dict[str, object] = {
        "id": 1,
        "symbol": "ENGRO",
        "company_name": "Engro Corporation Limited",
        "sector": "Fertilizer",
        "is_kmi_compliant": True,
        "is_kse100": True,
        "is_kse30": False,
        "market_cap_pkr": None,
        "shares_outstanding": None,
        "listed_at": None,
        "delisted_at": None,
        "is_active": True,
        "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    obj = MagicMock(spec=Security)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj  # type: ignore[return-value]


@pytest.fixture
def mock_session() -> AsyncSession:
    session = AsyncMock(spec=AsyncSession)
    return session  # type: ignore[return-value]


@pytest.fixture
async def client(mock_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """ASGI test client with get_db overridden to use the mock session."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_security() -> Security:
    return _make_security()


@pytest.fixture
def sample_security_response() -> SecurityResponse:
    return SecurityResponse(
        id=1,
        symbol="ENGRO",
        company_name="Engro Corporation Limited",
        sector="Fertilizer",
        is_kmi_compliant=True,
        is_kse100=True,
        is_kse30=False,
        market_cap_pkr=None,
        shares_outstanding=None,
        listed_at=None,
        delisted_at=None,
        is_active=True,
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_list_response(sample_security_response: SecurityResponse) -> SecuritiesListResponse:
    return SecuritiesListResponse(
        items=[sample_security_response],
        total=1,
        page=1,
        page_size=50,
        has_next=False,
    )


@pytest.fixture
def empty_ohlcv_response() -> OhlcvListResponse:
    return OhlcvListResponse(symbol="ENGRO", interval="daily", items=[], total=0)
