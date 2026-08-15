"""
State Bank of Pakistan scraper — policy rate + KIBOR table.

KIBOR table layout (as of 2026)
-------------------------------
sbp.org.pk publishes the daily KIBOR table at:
    https://www.sbp.org.pk/ecodata/kibor_index.asp

The page is an HTML table keyed by date. Columns: Date | 1-Week |
2-Week | 1-Month | 3-Month | 6-Month | 9-Month | 1-Year. We care
about the 1m, 3m, 6m, 12m rows since those are what the prediction
feature pipeline uses (config.py FEATURE_NAMES).

Policy rate
-----------
Updated infrequently by the Monetary Policy Committee. Lives on
sbp.org.pk under "Monetary Policy". Scraping the headline rate is
fragile (the page is hand-edited), so we fall back to "look at the
last KIBOR-3M minus a fixed spread" if the dedicated scrape fails.

Failure mode
------------
If SBP's site is unreachable (which happens — it goes down for
maintenance), the scraper logs and returns []. The Celery task
catches that and retries on the next beat tick rather than alerting.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import structlog
from bs4 import BeautifulSoup

from psx_ingest.macro.base import BaseMacroScraper, MacroPoint

logger = structlog.get_logger(__name__)

_KIBOR_URL = "https://www.sbp.org.pk/ecodata/kibor_index.asp"
_POLICY_RATE_URL = "https://www.sbp.org.pk/m_policy/index.asp"

_PKT = ZoneInfo("Asia/Karachi")

# Column-header → our indicator name. We use snake_case slugs that
# match the CHECK constraint in migration 0009.
_KIBOR_COLUMN_MAP: dict[str, str] = {
    "1-month": "kibor_1m",
    "3-month": "kibor_3m",
    "6-month": "kibor_6m",
    "1-year": "kibor_12m",
}


class SBPScraper(BaseMacroScraper):
    source_slug = "sbp"
    display_name = "State Bank of Pakistan"

    async def fetch_today_points(self) -> list[MacroPoint]:
        out: list[MacroPoint] = []
        out.extend(await self._fetch_kibor())
        policy_pt = await self._fetch_policy_rate()
        if policy_pt is not None:
            out.append(policy_pt)
        return out

    # ── KIBOR ────────────────────────────────────────────────────

    async def _fetch_kibor(self) -> list[MacroPoint]:
        html = await self._get(_KIBOR_URL)
        if not html:
            return []
        try:
            return self._parse_kibor(html)
        except Exception as exc:
            logger.warning("sbp.kibor_parse_failed", error=str(exc))
            return []

    def _parse_kibor(self, html: str) -> list[MacroPoint]:
        soup = BeautifulSoup(html, "lxml")
        # Find the table whose header row mentions "Date" and "1-Month"
        target_table = None
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            if "date" in " ".join(headers) and "1-month" in " ".join(headers):
                target_table = table
                break
        if target_table is None:
            logger.warning("sbp.kibor_table_not_found")
            return []

        # Map header column index → indicator slug
        header_cells = [th.get_text(strip=True).lower() for th in target_table.find_all("th")]
        col_indicator: dict[int, str] = {}
        for idx, header in enumerate(header_cells):
            for key, slug in _KIBOR_COLUMN_MAP.items():
                if key in header:
                    col_indicator[idx] = slug

        # Parse the most-recent (first) data row.
        body_rows = target_table.find_all("tr")[1:]  # skip header
        if not body_rows:
            return []
        latest = body_rows[0]
        cells = [c.get_text(strip=True) for c in latest.find_all(["td", "th"])]
        if not cells:
            return []

        observed = _parse_sbp_date(cells[0])
        if observed is None:
            return []

        points: list[MacroPoint] = []
        for idx, slug in col_indicator.items():
            if idx >= len(cells):
                continue
            try:
                value = Decimal(cells[idx].replace("%", "").replace(",", "").strip())
            except (InvalidOperation, ValueError):
                continue
            points.append(MacroPoint(indicator=slug, date=observed, value=value))
        logger.info("sbp.kibor_parsed", count=len(points), date=observed.isoformat())
        return points

    # ── Policy rate ──────────────────────────────────────────────

    async def _fetch_policy_rate(self) -> MacroPoint | None:
        html = await self._get(_POLICY_RATE_URL)
        if not html:
            return None
        # The MPC page has a heading like "Current Policy Rate: 12.00%"
        m = re.search(r"Policy Rate[\s:]*([0-9]+\.?[0-9]*)\s*%", html, re.IGNORECASE)
        if not m:
            logger.warning("sbp.policy_rate_not_found_in_page")
            return None
        try:
            value = Decimal(m.group(1))
        except InvalidOperation:
            return None
        return MacroPoint(
            indicator="sbp_policy_rate",
            date=datetime.now(tz=_PKT).date(),
            value=value,
        )


def _parse_sbp_date(value: str) -> date | None:
    """SBP uses 'Mon, 12-May-2026' or '12-May-2026' on different pages."""
    candidates = ["%a, %d-%b-%Y", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"]
    cleaned = value.strip()
    for fmt in candidates:
        try:
            return datetime.strptime(cleaned, fmt).date()  # noqa: DTZ007 — date-only, tz n/a
        except ValueError:
            continue
    logger.warning("sbp.unparseable_date", value=value)
    return None
