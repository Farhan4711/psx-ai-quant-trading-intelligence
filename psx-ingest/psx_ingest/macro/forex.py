"""
PKR/USD scraper — SBP daily interbank exchange rate.

SBP publishes the official interbank rate at:
    https://www.sbp.org.pk/ecodata/rates/m2m/M2M-Current.asp

The page is an HTML table with `Date | Bid | Offer` rows. We use the
mid (avg of bid + offer) as the canonical PKR/USD value.

For real-time / market rates (vs SBP's official benchmark), use a
forex aggregator — out of scope for v1 since the prediction features
expect a daily snapshot.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import structlog
from bs4 import BeautifulSoup

from psx_ingest.macro.base import BaseMacroScraper, MacroPoint

logger = structlog.get_logger(__name__)

_M2M_URL = "https://www.sbp.org.pk/ecodata/rates/m2m/M2M-Current.asp"
_PKT = ZoneInfo("Asia/Karachi")


class PkrUsdScraper(BaseMacroScraper):
    source_slug = "sbp_m2m"
    display_name = "SBP Interbank PKR/USD"

    async def fetch_today_points(self) -> list[MacroPoint]:
        html = await self._get(_M2M_URL)
        if not html:
            return []
        try:
            return self._parse(html)
        except Exception as exc:
            logger.warning("forex.parse_failed", error=str(exc))
            return []

    def _parse(self, html: str) -> list[MacroPoint]:
        soup = BeautifulSoup(html, "lxml")
        # Find a table that mentions both "Bid" and "Offer" in headers.
        target = None
        for table in soup.find_all("table"):
            headers = [
                th.get_text(strip=True).lower() for th in table.find_all("th")
            ]
            joined = " ".join(headers)
            if "bid" in joined and "offer" in joined:
                target = table
                break
        if target is None:
            logger.warning("forex.m2m_table_not_found")
            return []

        rows = target.find_all("tr")[1:]  # skip header
        if not rows:
            return []

        # The page lists multiple recent days; we take the first (newest)
        # row that parses cleanly.
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            try:
                observed = _try_parse_date(cells[0])
                bid = Decimal(cells[1].replace(",", ""))
                offer = Decimal(cells[2].replace(",", ""))
            except (InvalidOperation, ValueError):
                continue
            if observed is None:
                continue
            mid = ((bid + offer) / Decimal(2)).quantize(Decimal("0.0001"))
            logger.info(
                "forex.pkr_usd_parsed", date=observed.isoformat(), mid=str(mid)
            )
            return [MacroPoint(indicator="pkr_usd", date=observed, value=mid)]

        logger.warning("forex.no_parsable_rows")
        return []


def _try_parse_date(value: str) -> date | None:
    candidates = [
        "%a, %d-%b-%Y",
        "%d-%b-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]
    cleaned = value.strip()
    for fmt in candidates:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None
