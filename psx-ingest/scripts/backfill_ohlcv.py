# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk
# Internal reference: psx-docs/adr/ADR-000-psx-data-licensing.md

"""
One-off backfill: catches each active security up from its last stored
OHLCV date to today (PKT), using DpsScraper.fetch_ohlcv_range (one request
per month-chunk per symbol, rate-limited via settings.scraper_min_delay_seconds).

Usage:
    uv run python scripts/backfill_ohlcv.py
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.config import settings
from psx_ingest.scrapers.dps import DpsScraper
from psx_ingest.tasks.ohlcv import _upsert_rows

logger = structlog.get_logger(__name__)
_PKT = ZoneInfo("Asia/Karachi")


async def main() -> None:
    today = datetime.now(tz=_PKT).date()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        symbols_result = await session.execute(
            text("SELECT symbol FROM securities WHERE is_active = TRUE ORDER BY symbol")
        )
        symbols = [row[0] for row in symbols_result.fetchall()]

        last_dates_result = await session.execute(
            text("SELECT symbol, MAX(date) FROM ohlcv_daily GROUP BY symbol")
        )
        last_date_by_symbol: dict[str, date] = {
            row[0]: row[1] for row in last_dates_result.fetchall()
        }

    logger.info("Starting backfill", symbol_count=len(symbols), today=today.isoformat())

    total_rows = 0
    total_errors = 0

    async with DpsScraper() as scraper:
        for i, symbol in enumerate(symbols, start=1):
            last_date = last_date_by_symbol.get(symbol)
            from_date = (last_date + timedelta(days=1)) if last_date else date(today.year - 1, 1, 1)

            if from_date > today:
                continue

            try:
                rows = await scraper.fetch_ohlcv_range(symbol, from_date, today)
                async with session_factory() as session:
                    count = await _upsert_rows(session, rows)
                total_rows += count
                logger.info(
                    "Backfilled symbol",
                    symbol=symbol,
                    progress=f"{i}/{len(symbols)}",
                    from_date=from_date.isoformat(),
                    to_date=today.isoformat(),
                    rows=count,
                )
            except Exception as exc:
                total_errors += 1
                logger.error("Backfill failed for symbol", symbol=symbol, error=str(exc))

    await engine.dispose()
    logger.info("Backfill complete", total_rows=total_rows, total_errors=total_errors)


if __name__ == "__main__":
    asyncio.run(main())
