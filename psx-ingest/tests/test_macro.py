"""
Macro scraper tests — purely parser-level, no network.

SBP's HTML format changes occasionally so these tests are written
against fixture HTML matching the **expected** shape. When the live
site changes, update the fixtures here first, then fix the parser.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from psx_ingest.macro.forex import PkrUsdScraper
from psx_ingest.macro.sbp import SBPScraper, _parse_sbp_date


# ── SBP KIBOR ────────────────────────────────────────────────────


SAMPLE_KIBOR_HTML = """
<html><body>
<table>
  <tr><th>Date</th><th>1-Week</th><th>2-Week</th><th>1-Month</th>
      <th>3-Month</th><th>6-Month</th><th>9-Month</th><th>1-Year</th></tr>
  <tr><td>12-May-2026</td><td>11.85</td><td>11.90</td><td>12.10</td>
      <td>12.25</td><td>12.40</td><td>12.55</td><td>12.65</td></tr>
  <tr><td>09-May-2026</td><td>11.80</td><td>11.85</td><td>12.05</td>
      <td>12.20</td><td>12.35</td><td>12.50</td><td>12.60</td></tr>
</table>
</body></html>
"""


def test_kibor_parser_extracts_latest_row() -> None:
    scraper = SBPScraper()
    points = scraper._parse_kibor(SAMPLE_KIBOR_HTML)
    # We map 4 of the 7 KIBOR columns (1m, 3m, 6m, 12m).
    by_indicator = {p.indicator: p for p in points}
    assert "kibor_1m" in by_indicator
    assert "kibor_3m" in by_indicator
    assert "kibor_6m" in by_indicator
    assert "kibor_12m" in by_indicator
    assert by_indicator["kibor_1m"].value == Decimal("12.10")
    assert by_indicator["kibor_12m"].value == Decimal("12.65")
    assert by_indicator["kibor_1m"].date == date(2026, 5, 12)


def test_kibor_parser_handles_missing_table() -> None:
    scraper = SBPScraper()
    assert scraper._parse_kibor("<html><body>no tables here</body></html>") == []


def test_sbp_date_parser_handles_multiple_formats() -> None:
    assert _parse_sbp_date("12-May-2026") == date(2026, 5, 12)
    assert _parse_sbp_date("Mon, 12-May-2026") == date(2026, 5, 12)
    assert _parse_sbp_date("garbage") is None


# ── SBP M2M / PKR-USD ────────────────────────────────────────────


SAMPLE_M2M_HTML = """
<html><body>
<table>
  <tr><th>Date</th><th>Bid</th><th>Offer</th></tr>
  <tr><td>12-May-2026</td><td>278.50</td><td>278.80</td></tr>
  <tr><td>09-May-2026</td><td>278.40</td><td>278.70</td></tr>
</table>
</body></html>
"""


def test_pkr_usd_parser_uses_mid_of_bid_offer() -> None:
    scraper = PkrUsdScraper()
    points = scraper._parse(SAMPLE_M2M_HTML)
    assert len(points) == 1
    pt = points[0]
    assert pt.indicator == "pkr_usd"
    assert pt.date == date(2026, 5, 12)
    # mid = (278.50 + 278.80) / 2 = 278.65
    assert pt.value == Decimal("278.6500")


def test_pkr_usd_parser_skips_bad_rows() -> None:
    bad = """
    <html><body>
    <table>
      <tr><th>Date</th><th>Bid</th><th>Offer</th></tr>
      <tr><td>not a date</td><td>x</td><td>y</td></tr>
      <tr><td>12-May-2026</td><td>278.50</td><td>278.80</td></tr>
    </table>
    </body></html>
    """
    scraper = PkrUsdScraper()
    points = scraper._parse(bad)
    assert len(points) == 1
    assert points[0].value == Decimal("278.6500")
