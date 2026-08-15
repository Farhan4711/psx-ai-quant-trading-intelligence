# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk


"""
DPS (Data Portal System) scraper — fetches EOD OHLCV from dps.psx.com.pk.

## Endpoint change — v2 (2025-05)
The previously-used REST endpoint ``GET /timeseries/eod`` was decommissioned
by PSX.  The server now returns 404 + HTML for every request to that path.

The live endpoint is:
    POST https://dps.psx.com.pk/historical
    Content-Type: application/x-www-form-urlencoded
    Body: symbol=<TICKER>&from=<YYYY-MM-DD>&to=<YYYY-MM-DD>

The response is a server-rendered HTML fragment containing a ``<table>``
with columns: DATE | OPEN | HIGH | LOW | CLOSE | VOLUME.

Date cells carry a ``data-order`` Unix-timestamp attribute that is used for
sorting; we parse it as the authoritative date value when the text format
is ambiguous.

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
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from psx_ingest.config import settings

# Number of times to retry a request on transient network errors
_MAX_NETWORK_RETRIES = 3
_RETRY_SLEEP_SECONDS = 5.0

logger = structlog.get_logger(__name__)

_DPS_BASE = "https://dps.psx.com.pk"
_HISTORICAL_PATH = "/historical"

# Mimic a real browser session — DPS checks the Referer header on POST requests.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://dps.psx.com.pk/historical",
    "Origin": "https://dps.psx.com.pk",
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
    value_pkr: Decimal | None  # Not provided by /historical; always None


class ValidationError(Exception):
    """Raised when a scraped row fails data quality checks."""


class DpsScraper:
    """
    Async scraper for dps.psx.com.pk EOD data.

    Uses POST /historical which returns an HTML fragment containing a
    <table id="historicalTable"> with columns DATE|OPEN|HIGH|LOW|CLOSE|VOLUME.

    Enforces per-domain rate limiting via a shared timestamp so multiple
    instances in the same process don't race each other.
    """

    _last_request_time: float = 0.0
    _lock: asyncio.Lock | None = None

    def __init__(self, min_delay: float | None = None) -> None:
        self._min_delay = min_delay if min_delay is not None else settings.scraper_min_delay_seconds
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_ohlcv(self, symbol: str, trade_date: date) -> list[OhlcvRow]:
        """Fetch OHLCV for a single symbol on a single date."""
        raw = await self._post_historical(symbol, trade_date, trade_date)
        return self._parse_and_validate(symbol, raw, trade_date, trade_date)

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
            raw = await self._post_historical(symbol, chunk_start, chunk_end)
            rows.extend(self._parse_and_validate(symbol, raw, chunk_start, chunk_end))
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
                # Generous connect timeout — PSX TLS handshake can be slow.
                # http1=True forces HTTP/1.1; avoids h2 negotiation hangs.
                timeout=httpx.Timeout(60.0, connect=30.0),
                follow_redirects=True,
                http1=True,
                http2=False,
            )
        return self._client

    async def _rate_limited_post(self, url: str, data: dict[str, str]) -> httpx.Response:
        """POST with enforced inter-request delay and transient-error retry."""
        if DpsScraper._lock is None:
            DpsScraper._lock = asyncio.Lock()

        for attempt in range(1, _MAX_NETWORK_RETRIES + 1):
            try:
                async with DpsScraper._lock:
                    elapsed = time.monotonic() - DpsScraper._last_request_time
                    if elapsed < self._min_delay:
                        await asyncio.sleep(self._min_delay - elapsed)
                    client = await self._get_client()
                    response = await client.post(url, data=data)
                    DpsScraper._last_request_time = time.monotonic()

                response.raise_for_status()
                return response

            except (httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadTimeout) as exc:
                # Force a fresh client on the next attempt
                if self._client and not self._client.is_closed:
                    await self._client.aclose()
                self._client = None

                if attempt >= _MAX_NETWORK_RETRIES:
                    logger.error(
                        "DPS network error — giving up after retries",
                        url=url,
                        attempt=attempt,
                        error=str(exc),
                    )
                    raise

                logger.warning(
                    "DPS network error — will retry",
                    url=url,
                    attempt=attempt,
                    max_retries=_MAX_NETWORK_RETRIES,
                    error=str(exc),
                )
                await asyncio.sleep(_RETRY_SLEEP_SECONDS * attempt)

        # Should never reach here
        raise RuntimeError("_rate_limited_post: retry loop exhausted unexpectedly")

    async def _post_historical(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """
        Calls POST /historical and returns a list of raw OHLCV dicts.

        DPS responds with an HTML fragment:
            <div class="tbl__wrapper ...">
              <table id="historicalTable">
                <thead><tr><th>DATE</th><th>OPEN</th>...</tr></thead>
                <tbody>
                  <tr>
                    <td data-order="1735902000">Jan 3, 2025</td>
                    <td class="right">481.99</td>
                    ...
                  </tr>
                </tbody>
              </table>
            </div>

        The date cell carries a Unix timestamp in ``data-order`` which we
        use as the primary date source (avoids locale-parsing issues).
        """
        form_data = {
            "symbol": symbol.upper(),
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        }
        try:
            response = await self._rate_limited_post(_HISTORICAL_PATH, data=form_data)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "DPS /historical HTTP error",
                symbol=symbol,
                status_code=exc.response.status_code,
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
            )
            if exc.response.status_code in (404, 422):
                return []
            raise

        return self._parse_html_table(response.text, symbol)

    # ------------------------------------------------------------------
    # HTML parsing
    # ------------------------------------------------------------------

    def _parse_html_table(self, html: str, symbol: str) -> list[dict[str, Any]]:
        """
        Parses the HTML fragment returned by POST /historical.

        Expected column order: DATE | OPEN | HIGH | LOW | CLOSE | VOLUME
        (no VALUE/TURNOVER column — the endpoint does not provide it).
        """
        soup = BeautifulSoup(html, "lxml")
        table: Tag | None = soup.find("table")

        if not table:
            logger.warning(
                "DPS /historical returned no <table>",
                symbol=symbol,
                body_preview=html[:300],
            )
            return []

        rows: list[dict[str, Any]] = []
        tbody = table.find("tbody") or table

        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            # DATE — prefer data-order Unix timestamp for reliability
            date_td = tds[0]
            unix_ts: str | None = date_td.get("data-order")
            date_text = date_td.get_text(strip=True)

            rows.append(
                {
                    "_unix_ts": unix_ts,
                    "_date_text": date_text,
                    "OPEN": tds[1].get_text(strip=True).replace(",", ""),
                    "HIGH": tds[2].get_text(strip=True).replace(",", ""),
                    "LOW": tds[3].get_text(strip=True).replace(",", ""),
                    "CLOSE": tds[4].get_text(strip=True).replace(",", ""),
                    "VOLUME": tds[5].get_text(strip=True).replace(",", ""),
                }
            )

        return rows

    # ------------------------------------------------------------------
    # Parsing and validation
    # ------------------------------------------------------------------

    def _parse_and_validate(
        self,
        symbol: str,
        raw_rows: list[dict[str, Any]],
        from_date: date,
        to_date: date,
    ) -> list[OhlcvRow]:
        """
        Converts raw HTML-parsed dicts into validated OhlcvRow objects.
        Skips rows that fail validation and logs warnings rather than
        raising — callers should still persist healthy rows.
        """
        result: list[OhlcvRow] = []

        for raw in raw_rows:
            try:
                row = self._parse_row(symbol, raw)
                # Filter to the requested date window
                # (/historical may return data slightly outside the range)
                if not (from_date <= row.date <= to_date):
                    continue
                self._validate_row(row)
                result.append(row)
            except (KeyError, ValueError, ValidationError) as exc:
                logger.warning(
                    "Skipping invalid OHLCV row",
                    symbol=symbol,
                    raw=str(raw),
                    error=str(exc),
                )

        return result

    def _parse_row(self, symbol: str, raw: dict[str, Any]) -> OhlcvRow:
        """
        Parses one raw dict (from _parse_html_table) into an OhlcvRow.

        Date resolution order:
          1. data-order Unix timestamp (most reliable)
          2. Text content of the <td> (e.g. "Jan 3, 2025")
        """
        # ── Date ──────────────────────────────────────────────────────────────
        parsed_date: date | None = None

        unix_ts = raw.get("_unix_ts")
        if unix_ts:
            try:
                parsed_date = datetime.fromtimestamp(int(unix_ts), tz=UTC).date()
            except (ValueError, OSError):
                pass

        if parsed_date is None:
            date_text = raw.get("_date_text", "")
            for fmt in ("%b %d, %Y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y"):
                try:
                    parsed_date = datetime.strptime(  # noqa: DTZ007 — date-only, tz n/a
                        date_text.strip(), fmt
                    ).date()
                    break
                except ValueError:
                    continue

        if parsed_date is None:
            raise ValueError(f"Could not parse date from raw={raw!r}")

        # ── Numeric fields ────────────────────────────────────────────────────
        def _decimal(key: str) -> Decimal | None:
            v = raw.get(key, "")
            if not v or v in ("N/A", "-", ""):
                return None
            try:
                return Decimal(str(v))
            except InvalidOperation:
                return None

        def _int(key: str) -> int | None:
            v = raw.get(key, "")
            if not v or v in ("N/A", "-", ""):
                return None
            try:
                return int(float(str(v).replace(",", "")))
            except (ValueError, TypeError):
                return None

        return OhlcvRow(
            symbol=symbol.upper(),
            date=parsed_date,
            open=_decimal("OPEN"),
            high=_decimal("HIGH"),
            low=_decimal("LOW"),
            close=_decimal("CLOSE"),
            volume=_int("VOLUME"),
            value_pkr=None,  # /historical does not expose turnover value
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

    async def __aenter__(self) -> DpsScraper:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
