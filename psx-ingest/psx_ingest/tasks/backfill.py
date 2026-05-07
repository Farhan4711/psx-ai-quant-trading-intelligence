# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
One-time 5-year OHLCV backfill task.

Per LICENSING_NOTICE.md backfill policy:
  - Off-peak hours only (22:00–06:00 PKT)
  - 3-second minimum delay between requests (enforced by DPS scraper)
  - Raw JSON responses archived to R2 before DB insert

Typical run: 2–6 hours for ~400 active symbols × 5 years.
Run via:
    python -m psx_ingest.backfill                          # all symbols
    python -m psx_ingest.backfill --symbols ENGRO,LUCK     # specific symbols
    celery -A psx_ingest.worker call psx_ingest.tasks.backfill.backfill_ohlcv
"""

from __future__ import annotations

import asyncio
import gzip
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
_BACKFILL_YEARS = 5


def _date_range() -> tuple[date, date]:
    today = datetime.now(tz=_PKT).date()
    from_date = today.replace(year=today.year - _BACKFILL_YEARS)
    return from_date, today


async def _fetch_active_symbols(session: AsyncSession) -> list[str]:
    result = await session.execute(
        text("SELECT symbol FROM securities WHERE is_active = TRUE ORDER BY symbol")
    )
    return [row[0] for row in result.fetchall()]


async def _symbol_already_backfilled(session: AsyncSession, symbol: str, from_date: date) -> bool:
    """Returns True if the symbol already has data going back to from_date."""
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM ohlcv_daily
            WHERE symbol = :symbol AND date >= :from_date
        """),
        {"symbol": symbol, "from_date": from_date},
    )
    count = result.scalar_one()
    # Rough heuristic: if we have ≥900 rows (≈5y × 250 trading days × 72%)
    # we consider this symbol already backfilled
    return int(count) >= 900


async def _upsert_rows(session: AsyncSession, rows: list[OhlcvRow]) -> int:
    if not rows:
        return 0
    for row in rows:
        await session.execute(
            text("""
                INSERT INTO ohlcv_daily
                    (symbol, date, open, high, low, close, volume, value_pkr)
                VALUES
                    (:symbol, :date, :open, :high, :low, :close, :volume, :value_pkr)
                ON CONFLICT (symbol, date) DO NOTHING
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
    await session.commit()
    return len(rows)


async def _archive_to_r2(symbol: str, from_date: date, to_date: date, rows: list[OhlcvRow]) -> None:
    """
    Stores raw rows as gzipped JSON in R2/S3.
    Silently skips if storage is not configured (local dev).
    """
    if not settings.storage_endpoint_url:
        return

    try:
        import boto3  # type: ignore[import-not-found]

        payload = [
            {
                "symbol": r.symbol,
                "date": r.date.isoformat(),
                "open": str(r.open) if r.open else None,
                "high": str(r.high) if r.high else None,
                "low": str(r.low) if r.low else None,
                "close": str(r.close) if r.close else None,
                "volume": r.volume,
                "value_pkr": str(r.value_pkr) if r.value_pkr else None,
            }
            for r in rows
        ]
        body = gzip.compress(json.dumps(payload).encode())
        key = f"ohlcv/backfill/{symbol}/{from_date.isoformat()}_{to_date.isoformat()}.json.gz"

        client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key_id,
            aws_secret_access_key=settings.storage_secret_access_key,
        )
        client.put_object(Bucket=settings.storage_bucket_name, Key=key, Body=body)
        logger.debug("Archived to R2", symbol=symbol, key=key, rows=len(rows))

    except Exception as exc:
        # Archive failures are non-fatal — data is already in the DB
        logger.warning("R2 archive failed (non-fatal)", symbol=symbol, error=str(exc))


async def _run_backfill(
    symbols: list[str] | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    skip_existing: bool = True,
) -> dict[str, int]:
    default_from, default_to = _date_range()
    from_date = from_date or default_from
    to_date = to_date or default_to

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        target_symbols = symbols or await _fetch_active_symbols(session)

    total = len(target_symbols)
    symbols_ok = 0
    symbols_skipped = 0
    symbols_err = 0
    rows_inserted = 0

    logger.info(
        "Backfill starting",
        symbols=total,
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
        skip_existing=skip_existing,
    )

    async with DpsScraper() as scraper:
        for i, symbol in enumerate(target_symbols, 1):
            log = logger.bind(symbol=symbol, progress=f"{i}/{total}")

            try:
                if skip_existing:
                    async with session_factory() as session:
                        if await _symbol_already_backfilled(session, symbol, from_date):
                            log.debug("Skipping — already backfilled")
                            symbols_skipped += 1
                            continue

                rows = await scraper.fetch_ohlcv_range(symbol, from_date, to_date)

                if rows:
                    await _archive_to_r2(symbol, from_date, to_date, rows)
                    async with session_factory() as session:
                        inserted = await _upsert_rows(session, rows)
                    rows_inserted += inserted
                    log.info("Backfilled", rows=inserted)
                else:
                    log.debug("No data returned")

                symbols_ok += 1

            except Exception as exc:
                symbols_err += 1
                log.error("Backfill failed for symbol", error=str(exc))

    await engine.dispose()

    summary = {
        "symbols_ok": symbols_ok,
        "symbols_skipped": symbols_skipped,
        "symbols_err": symbols_err,
        "rows_inserted": rows_inserted,
        "total_symbols": total,
    }
    logger.info("Backfill complete", **summary)
    return summary


@celery_app.task(  # type: ignore[misc]
    name="psx_ingest.tasks.backfill.backfill_ohlcv",
    bind=True,
    max_retries=1,
    soft_time_limit=28800,   # 8 hours
    time_limit=32400,        # 9 hours hard limit
)
def backfill_ohlcv(
    self: object,
    symbols: list[str] | None = None,
    from_date_iso: str | None = None,
    to_date_iso: str | None = None,
    skip_existing: bool = True,
) -> dict[str, int]:
    """
    One-time 5-year OHLCV backfill.

    Args:
        symbols:        Optional list of symbols. Defaults to all active securities.
        from_date_iso:  ISO date string. Defaults to 5 years ago PKT.
        to_date_iso:    ISO date string. Defaults to today PKT.
        skip_existing:  Skip symbols that already have sufficient history.
    """
    from_date = date.fromisoformat(from_date_iso) if from_date_iso else None
    to_date = date.fromisoformat(to_date_iso) if to_date_iso else None

    return asyncio.run(
        _run_backfill(
            symbols=symbols,
            from_date=from_date,
            to_date=to_date,
            skip_existing=skip_existing,
        )
    )
