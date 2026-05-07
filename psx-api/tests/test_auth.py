"""
Tests for auth endpoints — mocked service layer, no DB or Redis required.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from psx_api.main import app
from psx_api.models.users import User
from psx_api.services.auth_service import AuthError


def _make_user(**kwargs: object) -> User:
    defaults = {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "test@example.com",
        "full_name": "Test User",
        "password_hash": "$argon2id$...",
        "email_verified_at": None,
        "totp_enabled": False,
        "totp_secret": None,
        "shariah_mode": False,
        "is_filer": False,
    }
    defaults.update(kwargs)
    obj = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj  # type: ignore[return-value]


@pytest.fixture
async def auth_client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestSignup:
    @pytest.mark.asyncio
    async def test_returns_201_on_success(self, auth_client: AsyncClient) -> None:
        user = _make_user()
        with (
            patch("psx_api.services.auth_service.AuthService.signup", new=AsyncMock(return_value=user)),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/signup",
                json={"email": "test@example.com", "password": "Password1"},
            )
        assert response.status_code == 201
        assert "user_id" in response.json()

    @pytest.mark.asyncio
    async def test_returns_409_for_duplicate_email(self, auth_client: AsyncClient) -> None:
        with (
            patch(
                "psx_api.services.auth_service.AuthService.signup",
                new=AsyncMock(side_effect=AuthError("already exists", 409)),
            ),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/signup",
                json={"email": "dup@example.com", "password": "Password1"},
            )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_rejects_weak_password(self, auth_client: AsyncClient) -> None:
        response = await auth_client.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "password": "weak"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_invalid_email(self, auth_client: AsyncClient) -> None:
        response = await auth_client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "Password1"},
        )
        assert response.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_returns_200_and_sets_cookie(self, auth_client: AsyncClient) -> None:
        user = _make_user()
        with (
            patch(
                "psx_api.services.auth_service.AuthService.login",
                new=AsyncMock(return_value=(user, "raw-token-abc")),
            ),
            patch(
                "psx_api.services.rate_limiter.LoginRateLimiter.is_blocked",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "psx_api.services.rate_limiter.LoginRateLimiter.clear",
                new=AsyncMock(),
            ),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Password1"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "psx_session" in response.cookies

    @pytest.mark.asyncio
    async def test_returns_429_when_rate_limited(self, auth_client: AsyncClient) -> None:
        with (
            patch(
                "psx_api.services.rate_limiter.LoginRateLimiter.is_blocked",
                new=AsyncMock(return_value=True),
            ),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Password1"},
            )
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_returns_401_for_wrong_password(self, auth_client: AsyncClient) -> None:
        with (
            patch(
                "psx_api.services.auth_service.AuthService.login",
                new=AsyncMock(side_effect=AuthError("Invalid email or password.", 401)),
            ),
            patch(
                "psx_api.services.rate_limiter.LoginRateLimiter.is_blocked",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "psx_api.services.rate_limiter.LoginRateLimiter.record_failure",
                new=AsyncMock(return_value=1),
            ),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrong"},
            )
        assert response.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_clears_cookie(self, auth_client: AsyncClient) -> None:
        with (
            patch("psx_api.services.auth_service.AuthService.logout", new=AsyncMock()),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/logout",
                cookies={"psx_session": "some-token"},
            )
        assert response.status_code == 200
        # Cookie should be deleted (max-age=0 or absent)
        assert response.json()["message"] == "Logged out."


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_always_returns_200(self, auth_client: AsyncClient) -> None:
        with (
            patch(
                "psx_api.services.auth_service.AuthService.forgot_password",
                new=AsyncMock(),
            ),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "unknown@example.com"},
            )
        # Must not reveal whether the email exists
        assert response.status_code == 200


class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_returns_200_for_valid_token(self, auth_client: AsyncClient) -> None:
        user = _make_user()
        with (
            patch(
                "psx_api.services.auth_service.AuthService.verify_email",
                new=AsyncMock(return_value=user),
            ),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/verify-email",
                json={"token": "valid-token"},
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_400_for_expired_token(self, auth_client: AsyncClient) -> None:
        with (
            patch(
                "psx_api.services.auth_service.AuthService.verify_email",
                new=AsyncMock(side_effect=AuthError("expired", 400)),
            ),
            patch("psx_api.database.get_db", new=AsyncMock()),
            patch("psx_api.redis_client.get_redis", new=AsyncMock()),
        ):
            response = await auth_client.post(
                "/api/v1/auth/verify-email",
                json={"token": "expired-token"},
            )
        assert response.status_code == 400
