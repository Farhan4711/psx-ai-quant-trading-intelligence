# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
Adjusted-price recomputation task.

Run after each corporate actions ingest to keep adjusted_close up to date.
Can also be triggered manually to recompute the full history for one or all symbols.

Celery beat schedule: runs at 18:00 PKT (after both ingest windows).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.adjustments import CorporateEvent, PriceRow, compute_adjusted_prices
from psx_ingest.config import settings
from psx_ingest.worker import celery_app

logger = structlog.get_logger(__name__)

_PKT = ZoneInfo("Asia/Karachi")


async def _fetch_active_symbols(session: AsyncSession) -> list[str]:
    result = await session.execute(
        text("SELECT symbol FROM securities WHERE is_active = TRUE ORDER BY symbol")
    )
    return [row[0] for row in result.fetchall()]


async def _fetch_prices(session: AsyncSession, symbol: str) -> list[PriceRow]:
    result = await session.execute(
        text("""
            SELECT date, close
            FROM ohlcv_daily
            WHERE symbol = :symbol AND close IS NOT NULL
            ORDER BY date ASC
        """),
        {"symbol": symbol},
    )
    return [PriceRow(date=row[0], close=Decimal(str(row[1]))) for row in result.fetchall()]


async def _fetch_events(session: AsyncSession, symbol: str) -> list[CorporateEvent]:
    result = await session.execute(
        text("""
            SELECT action_type, ex_date, announcement_date,
                   amount_per_share, ratio_numerator, ratio_denominator
            FROM corporate_actions
            WHERE symbol = :symbol
              AND action_type IN ('split', 'bonus', 'rights', 'dividend_cash')
              AND (ex_date IS NOT NULL OR announcement_date IS NOT NULL)
            ORDER BY COALESCE(ex_date, announcement_date) ASC
        """),
        {"symbol": symbol},
    )
    events = []
    for row in result.fetchall():
        action_type, ex_date_raw, ann_date_raw, amount_raw, num, den = row
        # Use ex_date if available, fall back to announcement_date as proxy
        effective_date: date = ex_date_raw or ann_date_raw
        events.append(CorporateEvent(
            ex_date=effective_date,
            action_type=action_type,
            amount_per_share=Decimal(str(amount_raw)) if amount_raw else None,
            ratio_numerator=int(num) if num else None,
            ratio_denominator=int(den) if den else None,
        ))
    return events


async def _write_adjusted_prices(
    session: AsyncSession,
    symbol: str,
    rows: list[PriceRow],
) -> int:
    """Bulk-updates adjusted_close for all rows of a symbol."""
    if not rows:
        return 0

    for row in rows:
        if row.adjusted_close is None:
            continue
        await session.execute(
            text("""
                UPDATE ohlcv_daily
                SET adjusted_close = :adj_close
                WHERE symbol = :symbol AND date = :date
            """),
            {
                "adj_close": float(row.adjusted_close),
                "symbol": symbol,
                "date": row.date,
            },
        )
    await session.commit()
    return len(rows)


async def _recompute_symbol(
    session_factory: async_sessionmaker[AsyncSession],
    symbol: str,
) -> int:
    async with session_factory() as session:
        prices = await _fetch_prices(session, symbol)
        events = await _fetch_events(session, symbol)

    if not prices:
        return 0

    adjusted = compute_adjusted_prices(prices, events)

    async with session_factory() as session:
        count = await _write_adjusted_prices(session, symbol, adjusted)

    return count


async def _run_recompute(symbols: list[str] | None = None) -> dict[str, int]:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        target = symbols or await _fetch_active_symbols(session)

    total_rows = 0
    symbols_ok = 0
    symbols_err = 0

    for symbol in target:
        try:
            count = await _recompute_symbol(session_factory, symbol)
            total_rows += count
            symbols_ok += 1
            logger.debug("Adjusted prices written", symbol=symbol, rows=count)
        except Exception as exc:
            symbols_err += 1
            logger.error("Failed to recompute adjusted prices", symbol=symbol, error=str(exc))

    await engine.dispose()

    summary = {
        "symbols_ok": symbols_ok,
        "symbols_err": symbols_err,
        "rows_updated": total_rows,
    }
    logger.info("Adjusted-price recompute complete", **summary)
    return summary


@celery_app.task(  # type: ignore[misc]
    name="psx_ingest.tasks.adjust_prices.recompute_adjusted_prices",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def recompute_adjusted_prices(
    self: object,
    symbols: list[str] | None = None,
) -> dict[str, int]:
    """
    Recomputes adjusted_close for all (or specific) active securities.
    Should be triggered after each corporate actions ingest.
    """
    try:
        return asyncio.run(_run_recompute(symbols))
    except Exception as exc:
        logger.error("recompute_adjusted_prices failed", error=str(exc))
        raise self.retry(exc=exc)  # type: ignore[attr-defined]
