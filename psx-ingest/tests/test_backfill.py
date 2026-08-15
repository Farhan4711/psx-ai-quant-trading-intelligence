"""
Tests for the OHLCV backfill task — logic only, no network or DB calls.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from psx_ingest.scrapers.dps import OhlcvRow
from psx_ingest.tasks.backfill import _archive_to_r2, _symbol_already_backfilled, _upsert_rows


def _make_row(symbol: str = "ENGRO", trade_date: date = date(2024, 1, 15)) -> OhlcvRow:
    return OhlcvRow(
        symbol=symbol,
        date=trade_date,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("99"),
        close=Decimal("103"),
        volume=500000,
        value_pkr=Decimal("51500000"),
    )


class TestUpsertRows:
    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_list(self) -> None:
        session = AsyncMock()
        result = await _upsert_rows(session, [])
        assert result == 0
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_count_of_rows(self) -> None:
        session = AsyncMock()
        rows = [_make_row(trade_date=date(2024, 1, i)) for i in range(1, 4)]
        result = await _upsert_rows(session, rows)
        assert result == 3
        assert session.execute.call_count == 3
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_on_conflict_do_nothing(self) -> None:
        session = AsyncMock()
        rows = [_make_row()]
        await _upsert_rows(session, rows)
        sql_text = str(session.execute.call_args_list[0][0][0])
        assert "ON CONFLICT" in sql_text
        assert "DO NOTHING" in sql_text


class TestSymbolAlreadyBackfilled:
    @pytest.mark.asyncio
    async def test_returns_true_when_count_exceeds_threshold(self) -> None:
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1200
        session.execute.return_value = mock_result

        result = await _symbol_already_backfilled(session, "ENGRO", date(2019, 1, 1))
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_count_below_threshold(self) -> None:
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 50
        session.execute.return_value = mock_result

        result = await _symbol_already_backfilled(session, "ENGRO", date(2019, 1, 1))
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_count_is_zero(self) -> None:
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        session.execute.return_value = mock_result

        result = await _symbol_already_backfilled(session, "NEW_SYM", date(2019, 1, 1))
        assert result is False


class TestArchiveToR2:
    @pytest.mark.asyncio
    async def test_skips_silently_when_storage_not_configured(self) -> None:
        with patch("psx_ingest.tasks.backfill.settings") as mock_settings:
            mock_settings.storage_endpoint_url = ""
            rows = [_make_row()]
            # Should not raise
            await _archive_to_r2("ENGRO", date(2024, 1, 1), date(2024, 1, 31), rows)

    @pytest.mark.asyncio
    async def test_skips_silently_on_boto3_error(self) -> None:
        with patch("psx_ingest.tasks.backfill.settings") as mock_settings:
            mock_settings.storage_endpoint_url = "https://r2.example.com"
            mock_settings.storage_access_key_id = "key"
            mock_settings.storage_secret_access_key = "secret"
            mock_settings.storage_bucket_name = "test-bucket"

            # boto3 is imported lazily inside _archive_to_r2 (avoids the import
            # cost when storage isn't configured), so there's no module-level
            # attribute to patch — patch the real boto3.client instead.
            with patch("boto3.client", side_effect=Exception("connection refused")):
                rows = [_make_row()]
                # Should not raise — archive failures are non-fatal
                await _archive_to_r2("ENGRO", date(2024, 1, 1), date(2024, 1, 31), rows)


class TestBackfillTask:
    def test_celery_task_is_registered(self) -> None:
        from psx_ingest.tasks.backfill import backfill_ohlcv

        assert callable(backfill_ohlcv)
        assert hasattr(backfill_ohlcv, "name")

    def test_task_name(self) -> None:
        from psx_ingest.tasks.backfill import backfill_ohlcv

        assert backfill_ohlcv.name == "psx_ingest.tasks.backfill.backfill_ohlcv"

    def test_task_accepts_date_strings(self) -> None:
        """Verify date parsing works without running the full task."""
        from psx_ingest.tasks.backfill import _date_range

        from_date, to_date = _date_range()
        assert isinstance(from_date, date)
        assert isinstance(to_date, date)
        assert (to_date - from_date).days > 365 * 4
