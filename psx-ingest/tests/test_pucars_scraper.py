"""
Unit tests for the PUCARS scraper — HTML/JSON parsing and helper functions.
No network calls are made.
"""

from datetime import date
from decimal import Decimal

import pytest

from psx_ingest.scrapers.pucars import (
    PucarsScraper,
    _extract_amount,
    _extract_date_by_label,
    _extract_ratio,
    _map_category,
    _parse_date_flexible,
)


class TestMapCategory:
    def test_maps_exact_dividend(self) -> None:
        assert _map_category("dividend") == "dividend_cash"

    def test_maps_cash_dividend(self) -> None:
        assert _map_category("Cash Dividend") == "dividend_cash"

    def test_maps_bonus_shares(self) -> None:
        assert _map_category("Bonus Shares") == "bonus"

    def test_maps_right_shares(self) -> None:
        assert _map_category("Right Shares") == "rights"

    def test_maps_agm(self) -> None:
        assert _map_category("AGM") == "agm"

    def test_maps_annual_general_meeting(self) -> None:
        assert _map_category("Annual General Meeting") == "agm"

    def test_maps_stock_split(self) -> None:
        assert _map_category("Stock Split") == "split"

    def test_maps_partial_match(self) -> None:
        assert _map_category("Final Cash Dividend") == "dividend_cash"

    def test_returns_none_for_unknown(self) -> None:
        assert _map_category("earnings release") is None

    def test_returns_none_for_empty(self) -> None:
        assert _map_category("") is None


class TestParseDateFlexible:
    def test_parses_iso_date(self) -> None:
        assert _parse_date_flexible("2024-01-15") == date(2024, 1, 15)

    def test_parses_dd_mon_yyyy(self) -> None:
        assert _parse_date_flexible("15-Jan-2024") == date(2024, 1, 15)

    def test_parses_dd_slash_mm_slash_yyyy(self) -> None:
        assert _parse_date_flexible("15/01/2024") == date(2024, 1, 15)

    def test_parses_dd_space_mon_space_yyyy(self) -> None:
        assert _parse_date_flexible("15 Jan 2024") == date(2024, 1, 15)

    def test_returns_none_for_empty(self) -> None:
        assert _parse_date_flexible("") is None

    def test_returns_none_for_unrecognised_format(self) -> None:
        assert _parse_date_flexible("01.15.2024") is None


class TestExtractAmount:
    def test_extracts_rs_amount(self) -> None:
        result = _extract_amount("Cash Dividend @ Rs. 2.50 per share")
        assert result == Decimal("2.50")

    def test_extracts_pkr_amount(self) -> None:
        result = _extract_amount("Dividend PKR 5 per share")
        assert result == Decimal("5")

    def test_extracts_at_sign_amount(self) -> None:
        result = _extract_amount("Bonus @10/share")
        assert result == Decimal("10")

    def test_returns_none_for_no_match(self) -> None:
        result = _extract_amount("Book closure announced")
        assert result is None


class TestExtractRatio:
    def test_extracts_n_for_m_pattern(self) -> None:
        num, den = _extract_ratio("1 share for every 5 held")
        assert num == 1
        assert den == 5

    def test_extracts_percentage_bonus(self) -> None:
        num, den = _extract_ratio("10% bonus issue")
        assert num == 10
        assert den == 100

    def test_extracts_colon_ratio(self) -> None:
        num, den = _extract_ratio("Bonus ratio 2:10")
        assert num == 2
        assert den == 10

    def test_returns_none_for_no_ratio(self) -> None:
        num, den = _extract_ratio("Cash dividend of Rs. 5")
        assert num is None
        assert den is None


class TestExtractDateByLabel:
    def test_extracts_ex_date(self) -> None:
        text = "Ex-Date: 15-Jan-2024. Record Date: 16-Jan-2024"
        result = _extract_date_by_label(text, r"ex[-\s]?date")
        assert result == date(2024, 1, 15)

    def test_extracts_record_date(self) -> None:
        text = "Ex-Date: 15-Jan-2024. Record Date: 16-Jan-2024"
        result = _extract_date_by_label(text, r"record[-\s]?date")
        assert result == date(2024, 1, 16)

    def test_returns_none_when_label_not_found(self) -> None:
        result = _extract_date_by_label("No dates here", r"ex[-\s]?date")
        assert result is None


class TestParseTableRow:
    @pytest.fixture
    def scraper(self) -> PucarsScraper:
        return PucarsScraper(min_delay=0.0)

    def test_parses_valid_dividend_row(self, scraper: PucarsScraper) -> None:
        cols = [
            "ENGRO",
            "Engro Corporation",
            "Cash Dividend",
            "2024-01-10",
            "Ex-Date: 15-Jan-2024 | Rs. 5.00 per share",
        ]
        row = scraper._parse_table_row(cols, date(2024, 1, 10))
        assert row is not None
        assert row.symbol == "ENGRO"
        assert row.action_type == "dividend_cash"
        assert row.announcement_date == date(2024, 1, 10)
        assert row.amount_per_share == Decimal("5.00")

    def test_parses_bonus_row_with_ratio(self, scraper: PucarsScraper) -> None:
        cols = [
            "LUCK",
            "Lucky Cement",
            "Bonus Shares",
            "2024-03-15",
            "10% bonus shares for every 100 held",
        ]
        row = scraper._parse_table_row(cols, date(2024, 3, 15))
        assert row is not None
        assert row.action_type == "bonus"
        assert row.ratio_denominator == 100

    def test_returns_none_for_unknown_category(self, scraper: PucarsScraper) -> None:
        cols = ["ENGRO", "Engro", "Earnings Release", "2024-01-10", ""]
        row = scraper._parse_table_row(cols, date(2024, 1, 10))
        assert row is None

    def test_returns_none_for_too_few_columns(self, scraper: PucarsScraper) -> None:
        row = scraper._parse_table_row(["ENGRO", "Engro"], date(2024, 1, 1))
        assert row is None

    def test_uses_fallback_date_when_date_unparseable(self, scraper: PucarsScraper) -> None:
        cols = ["PPL", "PPL", "AGM", "invalid-date", ""]
        fallback = date(2024, 5, 1)
        row = scraper._parse_table_row(cols, fallback)
        assert row is not None
        assert row.announcement_date == fallback


class TestParseAnnouncementsPage:
    @pytest.fixture
    def scraper(self) -> PucarsScraper:
        return PucarsScraper(min_delay=0.0)

    def test_parses_html_table(self, scraper: PucarsScraper) -> None:
        html = """
        <table>
          <tr><th>Symbol</th><th>Company</th><th>Category</th><th>Date</th><th>Details</th></tr>
          <tr>
            <td>ENGRO</td>
            <td>Engro Corporation</td>
            <td>Cash Dividend</td>
            <td>2024-01-10</td>
            <td>Rs. 5.00 per share | Ex-Date: 15-Jan-2024</td>
          </tr>
          <tr>
            <td>MCB</td>
            <td>MCB Bank</td>
            <td>Bonus Shares</td>
            <td>2024-01-12</td>
            <td>10% bonus for every 100 shares held</td>
          </tr>
        </table>
        """
        rows = scraper._parse_announcements_page(html, date(2024, 1, 10))
        assert len(rows) == 2
        assert rows[0].symbol == "ENGRO"
        assert rows[0].action_type == "dividend_cash"
        assert rows[1].symbol == "MCB"
        assert rows[1].action_type == "bonus"

    def test_returns_empty_for_no_table(self, scraper: PucarsScraper) -> None:
        rows = scraper._parse_announcements_page(
            "<html><body>No data</body></html>", date(2024, 1, 1)
        )
        assert rows == []

    def test_skips_header_row(self, scraper: PucarsScraper) -> None:
        html = """
        <table>
          <tr><th>Symbol</th><th>Company</th><th>Category</th><th>Date</th></tr>
        </table>
        """
        rows = scraper._parse_announcements_page(html, date(2024, 1, 1))
        assert rows == []

    def test_parses_json_fallback(self, scraper: PucarsScraper) -> None:
        import json

        data = [
            {
                "symbol": "LUCK",
                "category": "dividend",
                "DATE": "2024-02-01",
                "amount": "3.00",
            }
        ]
        rows = scraper._parse_announcements_page(json.dumps(data), date(2024, 2, 1))
        assert len(rows) == 1
        assert rows[0].symbol == "LUCK"
        assert rows[0].action_type == "dividend_cash"
