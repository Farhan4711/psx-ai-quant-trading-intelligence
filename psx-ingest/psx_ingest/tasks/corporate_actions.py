# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
Corporate actions ingestion task — scrapes PUCARS twice daily.

Scheduled via Celery beat at 09:00 and 17:30 PKT (see worker.py).
Fetches announcements for the trailing 30-day window and upserts
into the corporate_actions table, deduplicating on
(symbol, action_type, announcement_date).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.config import settings
from psx_ingest.scrapers.pucars import CorporateActionRow, PucarsScraper
from psx_ingest.worker import celery_app

logger = structlog.get_logger(__name__)

_PKT = ZoneInfo("Asia/Karachi")
_LOOKBACK_DAYS = 30


def _today_pkt() -> date:
    return datetime.now(tz=_PKT).date()


async def _upsert_action(session: AsyncSession, row: CorporateActionRow) -> bool:
    """
    Upserts a single corporate action.
    Deduplication key: (symbol, action_type, announcement_date).
    Returns True if a new row was inserted.
    """
    result = await session.execute(
        text("""
            INSERT INTO corporate_actions
                (symbol, action_type, announcement_date, ex_date, record_date,
                 payment_date, amount_per_share, ratio_numerator, ratio_denominator,
                 raw_announcement)
            VALUES
                (:symbol, :action_type, :announcement_date, :ex_date, :record_date,
                 :payment_date, :amount_per_share, :ratio_numerator, :ratio_denominator,
                 :raw_announcement)
            ON CONFLICT (symbol, action_type, announcement_date)
            DO UPDATE SET
                ex_date = COALESCE(EXCLUDED.ex_date, corporate_actions.ex_date),
                record_date = COALESCE(EXCLUDED.record_date, corporate_actions.record_date),
                payment_date = COALESCE(EXCLUDED.payment_date, corporate_actions.payment_date),
                amount_per_share = COALESCE(
                    EXCLUDED.amount_per_share, corporate_actions.amount_per_share
                ),
                ratio_numerator = COALESCE(
                    EXCLUDED.ratio_numerator, corporate_actions.ratio_numerator
                ),
                ratio_denominator = COALESCE(
                    EXCLUDED.ratio_denominator, corporate_actions.ratio_denominator
                ),
                raw_announcement = COALESCE(
                    EXCLUDED.raw_announcement, corporate_actions.raw_announcement
                )
            RETURNING (xmax = 0) AS was_inserted
        """),
        {
            "symbol": row.symbol,
            "action_type": row.action_type,
            "announcement_date": row.announcement_date,
            "ex_date": row.ex_date,
            "record_date": row.record_date,
            "payment_date": row.payment_date,
            "amount_per_share": float(row.amount_per_share) if row.amount_per_share else None,
            "ratio_numerator": row.ratio_numerator,
            "ratio_denominator": row.ratio_denominator,
            "raw_announcement": row.raw_announcement,
        },
    )
    row_result = result.fetchone()
    return bool(row_result and row_result[0])


async def _symbol_is_known(session: AsyncSession, symbol: str) -> bool:
    """Only insert actions for symbols that exist in our securities table."""
    result = await session.execute(
        text("SELECT 1 FROM securities WHERE symbol = :symbol"),
        {"symbol": symbol},
    )
    return result.fetchone() is not None


async def _run_ingest(from_date: date, to_date: date) -> dict[str, int]:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = 0
    updated = 0
    skipped_unknown = 0
    errors = 0

    async with PucarsScraper() as scraper:
        announcements = await scraper.fetch_announcements(from_date, to_date)
        logger.info(
            "PUCARS fetch complete",
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
            count=len(announcements),
        )

        async with session_factory() as session:
            for action in announcements:
                try:
                    if not await _symbol_is_known(session, action.symbol):
                        skipped_unknown += 1
                        continue

                    was_inserted = await _upsert_action(session, action)
                    if was_inserted:
                        inserted += 1
                    else:
                        updated += 1

                except Exception as exc:
                    errors += 1
                    logger.error(
                        "Failed to upsert corporate action",
                        symbol=action.symbol,
                        action_type=action.action_type,
                        error=str(exc),
                    )

            await session.commit()

    await engine.dispose()

    summary = {
        "inserted": inserted,
        "updated": updated,
        "skipped_unknown_symbol": skipped_unknown,
        "errors": errors,
        "total_fetched": len(announcements),
    }
    logger.info("Corporate actions ingest complete", **summary)
    return summary


@celery_app.task(  # type: ignore[misc]
    name="psx_ingest.tasks.corporate_actions.ingest_corporate_actions",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def ingest_corporate_actions(
    self: object,
    from_date_iso: str | None = None,
    to_date_iso: str | None = None,
) -> dict[str, int]:
    """
    Scrapes PUCARS for dividend declarations, bonus issues, rights issues,
    AGMs, and book-closure dates, then upserts into corporate_actions.

    Args:
        from_date_iso: ISO date string. Defaults to 30 days ago PKT.
        to_date_iso:   ISO date string. Defaults to today PKT.
    """
    today = _today_pkt()
    from_date = (
        date.fromisoformat(from_date_iso)
        if from_date_iso
        else today - timedelta(days=_LOOKBACK_DAYS)
    )
    to_date = date.fromisoformat(to_date_iso) if to_date_iso else today

    try:
        return asyncio.run(_run_ingest(from_date, to_date))
    except Exception as exc:
        logger.error("ingest_corporate_actions failed, will retry", error=str(exc))
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]
