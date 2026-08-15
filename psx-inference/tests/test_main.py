"""Tests for psx_inference.main — Sentry configuration and app lifespan."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from psx_inference.inference import ModelRegistry
from psx_inference.main import _configure_sentry, app, lifespan


@pytest.fixture(autouse=True)
def _reset_registry_singleton():  # type: ignore[no-untyped-def]
    ModelRegistry._instance = None
    yield
    ModelRegistry._instance = None


def test_configure_sentry_noop_without_dsn() -> None:
    with patch("psx_inference.main.settings") as mock_settings:
        mock_settings.sentry_dsn = ""
        with patch("sentry_sdk.init") as mock_init:
            _configure_sentry()
    mock_init.assert_not_called()


def test_configure_sentry_initialises_when_dsn_set() -> None:
    with patch("psx_inference.main.settings") as mock_settings:
        mock_settings.sentry_dsn = "https://example@sentry.io/1"
        mock_settings.environment = "test"
        with patch("sentry_sdk.init") as mock_init:
            _configure_sentry()
    mock_init.assert_called_once()
    assert mock_init.call_args.kwargs["dsn"] == "https://example@sentry.io/1"


@pytest.mark.asyncio
async def test_lifespan_loads_model_registry_on_startup() -> None:
    async with lifespan(app):
        registry = ModelRegistry.get()
        # lifespan calls ModelRegistry.get().load() — models dir doesn't
        # exist in the test env, so this is the safe "no models" path.
        assert registry._loaded is True
