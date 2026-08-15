# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
PUCARS scraper — parses PSX corporate action announcements from
dps.psx.com.pk/announcements (the Public Utility Corporate Announcement
Retrieval System).

Fetches announcements filtered by type and maps them to CorporateActionRow
objects that can be upserted into the corporate_actions table.

Rate-limiting policy: same 3-second minimum delay as the DPS OHLCV scraper.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from psx_ingest.config import settings

logger = structlog.get_logger(__name__)

_DPS_BASE = "https://dps.psx.com.pk"
_ANNOUNCEMENTS_PATH = "/announcements"
_HEADERS = {
    "User-Agent": (
        "PSX-AI-TradingSystem/0.1 (educational; non-commercial; contact: see LICENSING_NOTICE.md)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json",
}

# Mapping from PSX announcement category text → our internal action_type constants
_CATEGORY_MAP: dict[str, str] = {
    # Cash dividends
    "dividend": "dividend_cash",
    "cash dividend": "dividend_cash",
    "final dividend": "dividend_cash",
    "interim dividend": "dividend_cash",
    # Stock dividends / bonus
    "stock dividend": "dividend_stock",
    "bonus shares": "bonus",
    "bonus": "bonus",
    # Rights
    "right shares": "rights",
    "rights": "rights",
    # AGM / EGM
    "agm": "agm",
    "annual general meeting": "agm",
    "extraordinary general meeting": "agm",
    "egm": "agm",
    # Splits
    "stock split": "split",
    "split": "split",
}


@dataclass
class CorporateActionRow:
    symbol: str
    action_type: str
    announcement_date: date
    ex_date: date | None = None
    record_date: date | None = None
    payment_date: date | None = None
    amount_per_share: Decimal | None = None
    ratio_numerator: int | None = None
    ratio_denominator: int | None = None
    raw_announcement: str | None = None


class PucarsScraper:
    """
    Scrapes PUCARS announcement pages and parses them into CorporateActionRow objects.
    """

    _last_request_time: float = 0.0

    def __init__(self, min_delay: float | None = None) -> None:
        self._min_delay = min_delay if min_delay is not None else settings.scraper_min_delay_seconds
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_announcements(
        self,
        from_date: date,
        to_date: date,
        symbol: str | None = None,
    ) -> list[CorporateActionRow]:
        """
        Fetch corporate action announcements for a date range.
        Optionally filter by symbol.
        """
        params: dict[str, str] = {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        }
        if symbol:
            params["symbol"] = symbol.upper()

        try:
            response = await self._rate_limited_get(_ANNOUNCEMENTS_PATH, params)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "PUCARS HTTP error",
                status_code=exc.response.status_code,
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
            )
            return []

        return self._parse_announcements_page(response.text, from_date)

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

    async def _rate_limited_get(self, path: str, params: dict[str, str]) -> httpx.Response:
        elapsed = time.monotonic() - PucarsScraper._last_request_time
        if elapsed < self._min_delay:
            import asyncio

            await asyncio.sleep(self._min_delay - elapsed)

        client = await self._get_client()
        response = await client.get(path, params=params)
        PucarsScraper._last_request_time = time.monotonic()
        response.raise_for_status()
        return response

    # ------------------------------------------------------------------
    # HTML parsing
    # ------------------------------------------------------------------

    def _parse_announcements_page(self, html: str, fallback_date: date) -> list[CorporateActionRow]:
        """
        Parses the PUCARS HTML table.
        Expected columns: Symbol | Company | Category | Announcement Date | Details
        """
        soup = BeautifulSoup(html, "lxml")
        rows: list[CorporateActionRow] = []

        table = soup.find("table")
        if not table or not isinstance(table, Tag):
            # DPS might return JSON instead of HTML on some endpoints
            return self._parse_json_announcements(html, fallback_date)

        for tr in table.find_all("tr")[1:]:  # skip header row
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) < 4:
                continue

            row = self._parse_table_row(tds, fallback_date)
            if row:
                rows.append(row)

        return rows

    def _parse_json_announcements(self, text: str, fallback_date: date) -> list[CorporateActionRow]:
        """Fallback: parse JSON array if DPS returns JSON instead of HTML."""
        import json

        try:
            data = json.loads(text)
        except ValueError:
            return []

        if isinstance(data, dict):
            data = data.get("data", [])

        rows = []
        for item in data if isinstance(data, list) else []:
            row = self._parse_json_item(item, fallback_date)
            if row:
                rows.append(row)
        return rows

    def _parse_json_item(
        self, item: dict[str, Any], fallback_date: date
    ) -> CorporateActionRow | None:
        symbol = item.get("symbol") or item.get("SYMBOL")
        category = item.get("category") or item.get("CATEGORY") or ""
        action_type = _map_category(category)
        if not symbol or not action_type:
            return None

        ann_raw = item.get("announcement_date") or item.get("DATE") or ""
        ann_date = _parse_date_flexible(ann_raw) or fallback_date

        return CorporateActionRow(
            symbol=str(symbol).upper(),
            action_type=action_type,
            announcement_date=ann_date,
            ex_date=_parse_date_flexible(item.get("ex_date") or item.get("EX_DATE") or ""),
            record_date=_parse_date_flexible(
                item.get("record_date") or item.get("RECORD_DATE") or ""
            ),
            payment_date=_parse_date_flexible(
                item.get("payment_date") or item.get("PAYMENT_DATE") or ""
            ),
            amount_per_share=_parse_decimal(str(item.get("amount") or item.get("AMOUNT") or "")),
            raw_announcement=str(item),
        )

    def _parse_table_row(self, cols: list[str], fallback_date: date) -> CorporateActionRow | None:
        """
        Parses a single HTML table row.
        Expected column order: Symbol, Company, Category, Ann Date, [Details…]
        """
        if len(cols) < 4:
            return None

        symbol = cols[0].upper().strip()
        category_text = cols[2].lower().strip()
        action_type = _map_category(category_text)

        if not symbol or not action_type:
            return None

        ann_date = _parse_date_flexible(cols[3]) or fallback_date
        details_text = " | ".join(cols[4:]) if len(cols) > 4 else ""

        # Extract key dates and amounts from the details column
        ex_date = _extract_date_by_label(details_text, r"ex[-\s]?date")
        record_date = _extract_date_by_label(details_text, r"record[-\s]?date")
        payment_date = _extract_date_by_label(details_text, r"payment[-\s]?date|book closure")
        amount = _extract_amount(details_text)
        num, den = _extract_ratio(details_text)

        return CorporateActionRow(
            symbol=symbol,
            action_type=action_type,
            announcement_date=ann_date,
            ex_date=ex_date,
            record_date=record_date,
            payment_date=payment_date,
            amount_per_share=amount,
            ratio_numerator=num,
            ratio_denominator=den,
            raw_announcement=(details_text or None),
        )

    # ------------------------------------------------------------------
    # Resource cleanup
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> PucarsScraper:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# ------------------------------------------------------------------
# Helper functions (module-level for easy unit testing)
# ------------------------------------------------------------------


def _map_category(text: str) -> str | None:
    """Returns the internal action_type for a PSX category string, or None if unknown."""
    normalized = text.lower().strip()
    # Exact match first
    if normalized in _CATEGORY_MAP:
        return _CATEGORY_MAP[normalized]
    # Substring match
    for key, value in _CATEGORY_MAP.items():
        if key in normalized:
            return value
    return None


def _parse_date_flexible(text: str) -> date | None:
    """Tries multiple date formats; returns None if nothing matches."""
    if not text or not text.strip():
        return None
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()  # noqa: DTZ007 — date-only, tz n/a
        except ValueError:
            continue
    return None


def _parse_decimal(text: str) -> Decimal | None:
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _extract_date_by_label(text: str, label_pattern: str) -> date | None:
    """Searches `text` for a date that follows a label matching `label_pattern`."""
    pattern = (
        rf"{label_pattern}\s*[:\-]?\s*"
        rf"([\d]{{1,2}}[-/ ]{{1}}(?:\w+|\d{{2}})[-/ ]{{1}}\d{{2,4}}|\d{{4}}-\d{{2}}-\d{{2}})"
    )
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return _parse_date_flexible(match.group(1))
    return None


def _extract_amount(text: str) -> Decimal | None:
    """
    Extracts per-share amount from announcement text.
    Looks for patterns like "Rs. 2.50 per share", "PKR 5", "@2.5/share"
    """
    pattern = r"(?:rs\.?|pkr\.?|@)\s*([\d,]+\.?\d*)\s*(?:per\s+share)?/?\s*(?:share)?"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return _parse_decimal(match.group(1))
    return None


def _extract_ratio(text: str) -> tuple[int | None, int | None]:
    """
    Extracts bonus/rights ratio from text like "10% bonus" → (10, 100),
    "1 for 5" → (1, 5), "20 shares for every 100 held" → (20, 100).
    """
    # "N for M" or "N:M" patterns
    match = re.search(r"(\d+)\s*(?:shares?\s+)?(?:for|:)\s*(?:every\s+)?(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Percentage bonus: "10% bonus" → 10 shares for every 100
    match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:bonus|right)", text, re.IGNORECASE)
    if match:
        pct = float(match.group(1))
        # Normalise to integer ratio: 10% → 10:100, 12.5% → 1:8 (approx)
        numerator = int(round(pct))
        return numerator, 100

    return None, None
