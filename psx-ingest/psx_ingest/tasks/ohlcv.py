# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
Daily EOD OHLCV ingestion task.

Scheduled via Celery beat at 16:45 PKT (see worker.py).
For each active security, fetches today's EOD OHLCV from DPS and upserts
into the ohlcv_daily TimescaleDB hypertable.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.config import settings
from psx_ingest.scrapers.dps import DpsScraper, OhlcvRow
from psx_ingest.worker import celery_app

logger = structlog.get_logger(__name__)

_PKT = ZoneInfo("Asia/Karachi")


def _today_pkt() -> date:
    return datetime.now(tz=_PKT).date()


async def _fetch_active_symbols(session: AsyncSession) -> list[str]:
    result = await session.execute(
        text("SELECT symbol FROM securities WHERE is_active = TRUE ORDER BY symbol")
    )
    return [row[0] for row in result.fetchall()]


async def _upsert_rows(session: AsyncSession, rows: list[OhlcvRow]) -> int:
    if not rows:
        return 0

    upserted = 0
    for row in rows:
        await session.execute(
            text("""
                INSERT INTO ohlcv_daily
                    (symbol, date, open, high, low, close, volume, value_pkr)
                VALUES
                    (:symbol, :date, :open, :high, :low, :close, :volume, :value_pkr)
                ON CONFLICT (symbol, date)
                DO UPDATE SET
                    open      = EXCLUDED.open,
                    high      = EXCLUDED.high,
                    low       = EXCLUDED.low,
                    close     = EXCLUDED.close,
                    volume    = EXCLUDED.volume,
                    value_pkr = EXCLUDED.value_pkr
            """),
            {
                "symbol": row.symbol,
                "date": row.date,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
                "value_pkr": row.value_pkr,
            },
        )
        upserted += 1

    await session.commit()
    return upserted


async def _run_ingest(trade_date: date) -> dict[str, int]:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    symbols_ok: int = 0
    symbols_err: int = 0
    rows_upserted: int = 0

    async with DpsScraper() as scraper:
        async with session_factory() as session:
            symbols = await _fetch_active_symbols(session)
            logger.info("Starting EOD ingest", trade_date=trade_date.isoformat(), symbol_count=len(symbols))

        for symbol in symbols:
            try:
                rows = await scraper.fetch_ohlcv(symbol, trade_date)

                if not rows:
                    logger.debug("No data returned", symbol=symbol, trade_date=trade_date.isoformat())
                    symbols_ok += 1
                    continue

                async with session_factory() as session:
                    count = await _upsert_rows(session, rows)
                    rows_upserted += count

                symbols_ok += 1
                logger.debug("Ingested", symbol=symbol, rows=count)

            except Exception as exc:
                symbols_err += 1
                logger.error(
                    "Failed to ingest symbol",
                    symbol=symbol,
                    trade_date=trade_date.isoformat(),
                    error=str(exc),
                )

    await engine.dispose()

    summary = {
        "trade_date": trade_date.isoformat(),
        "symbols_ok": symbols_ok,
        "symbols_err": symbols_err,
        "rows_upserted": rows_upserted,
    }
    logger.info("EOD ingest complete", **summary)
    return {k: v for k, v in summary.items() if isinstance(v, int)}


@celery_app.task(  # type: ignore[misc]
    name="psx_ingest.tasks.ohlcv.ingest_eod_ohlcv",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5-minute backoff between retries
)
def ingest_eod_ohlcv(self: object, trade_date: str | None = None) -> dict[str, int]:
    """
    Fetches EOD OHLCV for all active PSX securities and upserts into TimescaleDB.

    Args:
        trade_date: ISO date string (YYYY-MM-DD). Defaults to today PKT.
                    Pass explicitly for backfill / manual re-runs.
    """
    target_date = date.fromisoformat(trade_date) if trade_date else _today_pkt()

    try:
        return asyncio.run(_run_ingest(target_date))
    except Exception as exc:
        logger.error("ingest_eod_ohlcv failed, will retry", error=str(exc), trade_date=target_date.isoformat())
        raise self.retry(exc=exc)  # type: ignore[attr-defined]
