# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
DPS (Data Portal System) scraper — fetches EOD OHLCV from dps.psx.com.pk.

Rate-limiting policy (see LICENSING_NOTICE.md):
- Minimum 3 seconds between requests to the same domain
- Backfills run off-peak (22:00–06:00 PKT) only
- No bulk exports beyond personal/educational use

Usage:
    scraper = DpsScraper()
    rows = await scraper.fetch_ohlcv("ENGRO", date(2024, 1, 15))
    history = await scraper.fetch_ohlcv_range("ENGRO", date(2023, 1, 1), date(2023, 12, 31))
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx
import structlog

from psx_ingest.config import settings

logger = structlog.get_logger(__name__)

_DPS_BASE = "https://dps.psx.com.pk"
_HEADERS = {
    "User-Agent": "PSX-AI-TradingSystem/0.1 (educational; non-commercial; contact: see LICENSING_NOTICE.md)",
    "Accept": "application/json, text/html",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class OhlcvRow:
    symbol: str
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None
    value_pkr: Decimal | None


class ValidationError(Exception):
    """Raised when a scraped row fails data quality checks."""


class DpsScraper:
    """
    Async scraper for dps.psx.com.pk EOD data.

    Enforces per-domain rate limiting via a shared timestamp so multiple
    instances in the same process don't race each other.
    """

    _last_request_time: float = 0.0
    _lock: asyncio.Lock | None = None

    def __init__(self, min_delay: float | None = None) -> None:
        self._min_delay = min_delay if min_delay is not None else settings.scraper_min_delay_seconds
        # Lazy-init lock per event loop to avoid "attached to a different loop" errors
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_ohlcv(self, symbol: str, trade_date: date) -> list[OhlcvRow]:
        """Fetch OHLCV for a single symbol on a single date."""
        raw = await self._get_ohlcv_json(symbol, trade_date, trade_date)
        return self._parse_and_validate(symbol, raw)

    async def fetch_ohlcv_range(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
    ) -> list[OhlcvRow]:
        """
        Fetch OHLCV for a symbol over a date range.
        Splits into monthly chunks to stay within DPS request limits.
        """
        rows: list[OhlcvRow] = []
        chunk_start = from_date

        while chunk_start <= to_date:
            # End of month, capped at to_date
            if chunk_start.month == 12:
                chunk_end = date(chunk_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                chunk_end = date(chunk_start.year, chunk_start.month + 1, 1) - timedelta(days=1)
            chunk_end = min(chunk_end, to_date)

            logger.debug(
                "Fetching OHLCV chunk",
                symbol=symbol,
                from_date=chunk_start.isoformat(),
                to_date=chunk_end.isoformat(),
            )
            raw = await self._get_ohlcv_json(symbol, chunk_start, chunk_end)
            rows.extend(self._parse_and_validate(symbol, raw))
            chunk_start = chunk_end + timedelta(days=1)

        return rows

    # ------------------------------------------------------------------
    # HTTP layer
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_DPS_BASE,
                headers=_HEADERS,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def _rate_limited_get(self, url: str, params: dict[str, Any]) -> httpx.Response:
        """GET with enforced inter-request delay."""
        if DpsScraper._lock is None:
            DpsScraper._lock = asyncio.Lock()

        async with DpsScraper._lock:
            elapsed = time.monotonic() - DpsScraper._last_request_time
            if elapsed < self._min_delay:
                await asyncio.sleep(self._min_delay - elapsed)
            client = await self._get_client()
            response = await client.get(url, params=params)
            DpsScraper._last_request_time = time.monotonic()

        response.raise_for_status()
        return response

    async def _get_ohlcv_json(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """
        Calls the DPS OHLCV endpoint.

        DPS returns a JSON array of objects. The endpoint format is:
          GET /timeseries/eod?symbol=ENGRO&from=2024-01-01&to=2024-01-31
        """
        params = {
            "symbol": symbol.upper(),
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        }
        try:
            response = await self._rate_limited_get("/timeseries/eod", params=params)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "DPS HTTP error",
                symbol=symbol,
                status_code=exc.response.status_code,
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
            )
            if exc.response.status_code == 404:
                return []
            raise

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            # DPS sometimes redirects to an HTML page for unknown symbols
            logger.warning(
                "DPS returned non-JSON response",
                symbol=symbol,
                content_type=content_type,
            )
            return []

        data = response.json()
        if isinstance(data, dict):
            # Some endpoints wrap in {"data": [...]}
            data = data.get("data", [])
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------------
    # Parsing and validation
    # ------------------------------------------------------------------

    def _parse_and_validate(
        self,
        symbol: str,
        raw_rows: list[dict[str, Any]],
    ) -> list[OhlcvRow]:
        """
        Converts raw DPS JSON rows into validated OhlcvRow objects.
        Skips rows that fail validation and logs warnings rather than
        raising — callers should still persist healthy rows.
        """
        result: list[OhlcvRow] = []

        for raw in raw_rows:
            try:
                row = self._parse_row(symbol, raw)
                self._validate_row(row)
                result.append(row)
            except (KeyError, ValueError, ValidationError) as exc:
                logger.warning(
                    "Skipping invalid OHLCV row",
                    symbol=symbol,
                    raw=json.dumps(raw, default=str),
                    error=str(exc),
                )

        return result

    def _parse_row(self, symbol: str, raw: dict[str, Any]) -> OhlcvRow:
        """
        DPS field mapping (field names observed in practice):
          DATE / date / TRADEDATE  → date
          OPEN / open / O          → open
          HIGH / high / H          → high
          LOW  / low  / L          → low
          CLOSE/ close/ C          → close
          VOLUME/volume/VOL        → volume
          VALUE/ value / TURNOVER  → value_pkr
        """

        def _get(*keys: str) -> Any:
            for k in keys:
                if k in raw:
                    return raw[k]
            return None

        def _decimal(v: Any) -> Decimal | None:
            if v is None or v == "" or v == "N/A":
                return None
            return Decimal(str(v))

        def _int(v: Any) -> int | None:
            if v is None or v == "" or v == "N/A":
                return None
            return int(float(str(v)))

        date_val = _get("DATE", "date", "TRADEDATE", "trade_date")
        if date_val is None:
            raise ValueError("Missing date field")

        if isinstance(date_val, str):
            # Accept both YYYY-MM-DD and DD-MMM-YYYY (e.g. "15-Jan-2024")
            for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
                try:
                    parsed_date = date.fromisoformat(date_val) if fmt == "%Y-%m-%d" else date(*time.strptime(date_val, fmt)[:3])
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Unrecognised date format: {date_val!r}")
        elif isinstance(date_val, date):
            parsed_date = date_val
        else:
            raise ValueError(f"Unexpected date type: {type(date_val)}")

        return OhlcvRow(
            symbol=symbol.upper(),
            date=parsed_date,
            open=_decimal(_get("OPEN", "open", "O")),
            high=_decimal(_get("HIGH", "high", "H")),
            low=_decimal(_get("LOW", "low", "L")),
            close=_decimal(_get("CLOSE", "close", "C", "LDCP")),
            volume=_int(_get("VOLUME", "volume", "VOL", "TOTALVOL")),
            value_pkr=_decimal(_get("VALUE", "value", "TURNOVER", "TOTALVAL")),
        )

    @staticmethod
    def _validate_row(row: OhlcvRow) -> None:
        """
        Data quality guards per Step 11 acceptance criteria:
        - No negative volumes
        - No zero open prices (when present)
        - Flag >50% single-day swing (high/low spread relative to open)
        """
        if row.volume is not None and row.volume < 0:
            raise ValidationError(f"Negative volume {row.volume} on {row.date}")

        if row.open is not None and row.open == Decimal("0"):
            raise ValidationError(f"Zero open price on {row.date}")

        if row.high is not None and row.low is not None and row.open is not None:
            if row.open > Decimal("0"):
                swing = (row.high - row.low) / row.open
                if swing > Decimal("0.5"):
                    # Don't raise — flag so caller can attach for-review note
                    logger.warning(
                        "Large intraday swing — verify against announcements",
                        symbol=row.symbol,
                        date=row.date.isoformat(),
                        swing_pct=float(swing * 100),
                    )

    # ------------------------------------------------------------------
    # Resource cleanup
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "DpsScraper":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
