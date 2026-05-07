"""
Tests for GET /api/v1/securities, GET /api/v1/securities/{symbol},
GET /api/v1/securities/{symbol}/ohlcv, GET /api/v1/sectors.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from psx_api.schemas.securities import OhlcvListResponse, SecuritiesListResponse, SecurityResponse


class TestListSecurities:
    @pytest.mark.asyncio
    async def test_returns_200_with_list(
        self,
        client: AsyncClient,
        sample_list_response: SecuritiesListResponse,
    ) -> None:
        with patch(
            "psx_api.services.securities_service.SecuritiesService.list_securities",
            new=AsyncMock(return_value=sample_list_response),
        ):
            response = await client.get("/api/v1/securities")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert data["has_next"] is False
        assert len(data["items"]) == 1
        assert data["items"][0]["symbol"] == "ENGRO"

    @pytest.mark.asyncio
    async def test_pagination_params_forwarded(
        self,
        client: AsyncClient,
        sample_list_response: SecuritiesListResponse,
    ) -> None:
        mock = AsyncMock(return_value=sample_list_response)
        with patch(
            "psx_api.services.securities_service.SecuritiesService.list_securities",
            new=mock,
        ):
            await client.get("/api/v1/securities?page=2&page_size=10")

        mock.assert_called_once()
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 10

    @pytest.mark.asyncio
    async def test_filter_params_forwarded(
        self,
        client: AsyncClient,
        sample_list_response: SecuritiesListResponse,
    ) -> None:
        mock = AsyncMock(return_value=sample_list_response)
        with patch(
            "psx_api.services.securities_service.SecuritiesService.list_securities",
            new=mock,
        ):
            await client.get("/api/v1/securities?sector=Fertilizer&kmi_only=true&kse100_only=true&search=eng")

        call_kwargs = mock.call_args.kwargs
        assert call_kwargs["sector"] == "Fertilizer"
        assert call_kwargs["kmi_only"] is True
        assert call_kwargs["kse100_only"] is True
        assert call_kwargs["search"] == "eng"

    @pytest.mark.asyncio
    async def test_invalid_page_size_returns_422(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/securities?page_size=999")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_shape_has_required_fields(
        self,
        client: AsyncClient,
        sample_list_response: SecuritiesListResponse,
    ) -> None:
        with patch(
            "psx_api.services.securities_service.SecuritiesService.list_securities",
            new=AsyncMock(return_value=sample_list_response),
        ):
            response = await client.get("/api/v1/securities")

        data = response.json()
        assert set(data.keys()) == {"items", "total", "page", "page_size", "has_next"}


class TestGetSecurity:
    @pytest.mark.asyncio
    async def test_returns_security_for_known_symbol(
        self,
        client: AsyncClient,
        sample_security_response: SecurityResponse,
    ) -> None:
        with patch(
            "psx_api.services.securities_service.SecuritiesService.get_security",
            new=AsyncMock(return_value=sample_security_response),
        ):
            response = await client.get("/api/v1/securities/ENGRO")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "ENGRO"
        assert data["company_name"] == "Engro Corporation Limited"
        assert data["sector"] == "Fertilizer"
        assert data["is_kmi_compliant"] is True

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_symbol(self, client: AsyncClient) -> None:
        with patch(
            "psx_api.services.securities_service.SecuritiesService.get_security",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get("/api/v1/securities/FAKESYM")

        assert response.status_code == 404
        assert "FAKESYM" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_symbol_lookup_is_case_insensitive(
        self,
        client: AsyncClient,
        sample_security_response: SecurityResponse,
    ) -> None:
        mock = AsyncMock(return_value=sample_security_response)
        with patch(
            "psx_api.services.securities_service.SecuritiesService.get_security",
            new=mock,
        ):
            response = await client.get("/api/v1/securities/engro")

        assert response.status_code == 200


class TestGetOhlcv:
    @pytest.mark.asyncio
    async def test_returns_ohlcv_data(
        self,
        client: AsyncClient,
        sample_security_response: SecurityResponse,
        empty_ohlcv_response: OhlcvListResponse,
    ) -> None:
        with (
            patch(
                "psx_api.services.securities_service.SecuritiesService.get_security",
                new=AsyncMock(return_value=sample_security_response),
            ),
            patch(
                "psx_api.services.securities_service.SecuritiesService.get_ohlcv",
                new=AsyncMock(return_value=empty_ohlcv_response),
            ),
        ):
            response = await client.get("/api/v1/securities/ENGRO/ohlcv")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "ENGRO"
        assert data["interval"] == "daily"
        assert "items" in data

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_symbol(self, client: AsyncClient) -> None:
        with patch(
            "psx_api.services.securities_service.SecuritiesService.get_security",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get("/api/v1/securities/FAKESYM/ohlcv")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_limit_param_capped_at_2000(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/securities/ENGRO/ohlcv?limit=9999")
        assert response.status_code == 422


class TestListSectors:
    @pytest.mark.asyncio
    async def test_returns_list_of_strings(self, client: AsyncClient) -> None:
        sectors = ["Cement", "Fertilizer", "Oil & Gas Exploration"]
        with patch(
            "psx_api.services.securities_service.SecuritiesService.list_sectors",
            new=AsyncMock(return_value=sectors),
        ):
            response = await client.get("/api/v1/sectors")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "Fertilizer" in data

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_sectors(self, client: AsyncClient) -> None:
        with patch(
            "psx_api.services.securities_service.SecuritiesService.list_sectors",
            new=AsyncMock(return_value=[]),
        ):
            response = await client.get("/api/v1/sectors")

        assert response.status_code == 200
        assert response.json() == []
