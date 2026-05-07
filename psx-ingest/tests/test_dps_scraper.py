"""
Unit tests for DPS scraper — parsing and validation logic only.
No network calls are made.
"""

from datetime import date
from decimal import Decimal

import pytest

from psx_ingest.scrapers.dps import DpsScraper, OhlcvRow, ValidationError


@pytest.fixture
def scraper() -> DpsScraper:
    return DpsScraper(min_delay=0.0)


class TestParseRow:
    def test_parses_standard_json_fields(self, scraper: DpsScraper) -> None:
        raw = {
            "DATE": "2024-01-15",
            "OPEN": "120.50",
            "HIGH": "125.00",
            "LOW": "119.00",
            "CLOSE": "123.75",
            "VOLUME": "1500000",
            "VALUE": "185625000.00",
        }
        row = scraper._parse_row("ENGRO", raw)
        assert row.symbol == "ENGRO"
        assert row.date == date(2024, 1, 15)
        assert row.open == Decimal("120.50")
        assert row.high == Decimal("125.00")
        assert row.low == Decimal("119.00")
        assert row.close == Decimal("123.75")
        assert row.volume == 1500000
        assert row.value_pkr == Decimal("185625000.00")

    def test_parses_lowercase_field_names(self, scraper: DpsScraper) -> None:
        raw = {
            "date": "2024-02-01",
            "open": "50.00",
            "high": "52.00",
            "low": "49.00",
            "close": "51.00",
            "volume": "200000",
            "value": "10200000.00",
        }
        row = scraper._parse_row("LUCK", raw)
        assert row.date == date(2024, 2, 1)
        assert row.symbol == "LUCK"

    def test_parses_short_field_names(self, scraper: DpsScraper) -> None:
        raw = {
            "DATE": "2024-03-10",
            "O": "100.00",
            "H": "105.00",
            "L": "99.00",
            "C": "103.00",
            "VOL": "500000",
        }
        row = scraper._parse_row("MCB", raw)
        assert row.open == Decimal("100.00")
        assert row.close == Decimal("103.00")
        assert row.volume == 500000
        assert row.value_pkr is None

    def test_symbol_normalised_to_uppercase(self, scraper: DpsScraper) -> None:
        raw = {"date": "2024-01-01", "open": "10", "high": "11", "low": "9", "close": "10"}
        row = scraper._parse_row("ppl", raw)
        assert row.symbol == "PPL"

    def test_handles_none_volume_gracefully(self, scraper: DpsScraper) -> None:
        raw = {"DATE": "2024-01-15", "OPEN": "100", "HIGH": "101", "LOW": "99", "CLOSE": "100"}
        row = scraper._parse_row("TRG", raw)
        assert row.volume is None

    def test_handles_na_string_as_none(self, scraper: DpsScraper) -> None:
        raw = {
            "DATE": "2024-01-15",
            "OPEN": "N/A",
            "HIGH": "N/A",
            "LOW": "N/A",
            "CLOSE": "100.00",
            "VOLUME": "N/A",
        }
        row = scraper._parse_row("SEARL", raw)
        assert row.open is None
        assert row.volume is None
        assert row.close == Decimal("100.00")

    def test_raises_on_missing_date(self, scraper: DpsScraper) -> None:
        raw = {"OPEN": "100", "CLOSE": "100"}
        with pytest.raises(ValueError, match="Missing date field"):
            scraper._parse_row("ENGRO", raw)

    def test_raises_on_unrecognised_date_format(self, scraper: DpsScraper) -> None:
        raw = {"DATE": "01.15.2024", "OPEN": "100", "CLOSE": "100"}
        with pytest.raises(ValueError, match="Unrecognised date format"):
            scraper._parse_row("ENGRO", raw)


class TestValidateRow:
    def test_valid_row_passes(self) -> None:
        row = OhlcvRow(
            symbol="ENGRO",
            date=date(2024, 1, 15),
            open=Decimal("120"),
            high=Decimal("125"),
            low=Decimal("119"),
            close=Decimal("123"),
            volume=1000000,
            value_pkr=Decimal("123000000"),
        )
        DpsScraper._validate_row(row)  # should not raise

    def test_raises_on_negative_volume(self) -> None:
        row = OhlcvRow(
            symbol="ENGRO",
            date=date(2024, 1, 15),
            open=Decimal("120"),
            high=Decimal("125"),
            low=Decimal("119"),
            close=Decimal("123"),
            volume=-1,
            value_pkr=None,
        )
        with pytest.raises(ValidationError, match="Negative volume"):
            DpsScraper._validate_row(row)

    def test_raises_on_zero_open(self) -> None:
        row = OhlcvRow(
            symbol="ENGRO",
            date=date(2024, 1, 15),
            open=Decimal("0"),
            high=Decimal("5"),
            low=Decimal("0"),
            close=Decimal("5"),
            volume=100,
            value_pkr=None,
        )
        with pytest.raises(ValidationError, match="Zero open price"):
            DpsScraper._validate_row(row)

    def test_skips_volume_check_when_none(self) -> None:
        row = OhlcvRow(
            symbol="ENGRO",
            date=date(2024, 1, 15),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=None,
            value_pkr=None,
        )
        DpsScraper._validate_row(row)  # should not raise

    def test_large_swing_does_not_raise(self) -> None:
        """Large swings are flagged as warnings but do not raise — row is kept."""
        row = OhlcvRow(
            symbol="ENGRO",
            date=date(2024, 1, 15),
            open=Decimal("100"),
            high=Decimal("160"),
            low=Decimal("40"),
            close=Decimal("100"),
            volume=100000,
            value_pkr=None,
        )
        DpsScraper._validate_row(row)  # should not raise, just logs warning


class TestParseAndValidate:
    def test_skips_invalid_rows_and_keeps_valid(self, scraper: DpsScraper) -> None:
        raw_rows = [
            # Valid row
            {
                "DATE": "2024-01-15",
                "OPEN": "100",
                "HIGH": "105",
                "LOW": "99",
                "CLOSE": "103",
                "VOLUME": "100000",
            },
            # Invalid — negative volume
            {
                "DATE": "2024-01-16",
                "OPEN": "103",
                "HIGH": "106",
                "LOW": "102",
                "CLOSE": "105",
                "VOLUME": "-1",
            },
            # Invalid — missing date
            {"OPEN": "99", "CLOSE": "100"},
        ]
        result = scraper._parse_and_validate("ENGRO", raw_rows)
        assert len(result) == 1
        assert result[0].date.isoformat() == "2024-01-15"

    def test_returns_empty_list_for_empty_input(self, scraper: DpsScraper) -> None:
        assert scraper._parse_and_validate("ENGRO", []) == []

    def test_wraps_data_key_pattern(self, scraper: DpsScraper) -> None:
        """DPS sometimes returns {"data": [...]} — handled in _get_ohlcv_json, not here."""
        raw_rows = [
            {"DATE": "2024-01-15", "OPEN": "100", "HIGH": "102", "LOW": "99", "CLOSE": "101"},
        ]
        result = scraper._parse_and_validate("ENGRO", raw_rows)
        assert len(result) == 1
