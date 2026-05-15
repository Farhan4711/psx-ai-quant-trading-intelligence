"""
Common HTTP + retry primitives for macro scrapers. Thinner than the
news base because macro sources are tiny tables, not feeds.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import httpx
import structlog

from psx_ingest.config import settings

logger = structlog.get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "PSX-AI-TradingSystem/0.1 (educational; non-commercial; "
        "contact: see LICENSING_NOTICE.md)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}


@dataclass(frozen=True)
class MacroPoint:
    """One observation ready to upsert into `macro_indicators`."""

    indicator: str
    date: date
    value: Decimal


class MacroFetchError(Exception):
    """Raised when an upstream source returns garbage we can't parse."""


class BaseMacroScraper:
    """Subclass and implement `fetch_today_points()`."""

    source_slug: str = "base"
    display_name: str = "Base"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client_external = client is not None
        self._client = client
        self._last_request_at: float = 0.0

    async def __aenter__(self) -> "BaseMacroScraper":
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=_HEADERS,
                timeout=httpx.Timeout(20.0),
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if not self._client_external and self._client is not None:
            await self._client.aclose()

    async def _get(self, url: str) -> str | None:
        await self._throttle()
        assert self._client is not None
        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            logger.warning(
                "macro.http_error",
                source=self.source_slug,
                url=url,
                error=str(exc),
            )
            return None
        if resp.status_code >= 400:
            logger.warning(
                "macro.bad_status",
                source=self.source_slug,
                url=url,
                status=resp.status_code,
            )
            return None
        return resp.text

    async def _throttle(self) -> None:
        min_delay = max(settings.scraper_min_delay_seconds, 1.0)
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < min_delay:
            await asyncio.sleep(min_delay - elapsed)
        self._last_request_at = time.monotonic()

    async def fetch_today_points(self) -> list[MacroPoint]:
        raise NotImplementedError
