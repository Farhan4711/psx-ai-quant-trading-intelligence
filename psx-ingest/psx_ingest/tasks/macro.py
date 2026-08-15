"""
Macro indicator daily ingest.

Runs once per day at 17:00 PKT (after market close, when SBP has
posted the day's KIBOR table). Single Celery task scrapes all the
SBP-hosted indicators in sequence — they're tiny tables, so there's
no benefit to fanning out.
"""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.config import settings
from psx_ingest.macro.base import MacroPoint
from psx_ingest.macro.forex import PkrUsdScraper
from psx_ingest.macro.sbp import SBPScraper
from psx_ingest.worker import celery_app

logger = structlog.get_logger(__name__)


async def _upsert_point(session: AsyncSession, point: MacroPoint) -> bool:
    """Upserts one observation. Returns True if a new row was inserted."""
    result = await session.execute(
        text(
            """
            INSERT INTO macro_indicators (indicator, date, value)
            VALUES (:indicator, :date, :value)
            ON CONFLICT (indicator, date)
            DO UPDATE SET value = EXCLUDED.value
            RETURNING (xmax = 0) AS was_inserted
            """
        ),
        {
            "indicator": point.indicator,
            "date": point.date,
            "value": float(point.value),
        },
    )
    row = result.fetchone()
    return bool(row and row[0])


async def _run() -> dict[str, int]:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    points: list[MacroPoint] = []
    async with SBPScraper() as sbp:
        points.extend(await sbp.fetch_today_points())
    async with PkrUsdScraper() as fx:
        points.extend(await fx.fetch_today_points())

    inserted = 0
    updated = 0
    errors = 0
    async with session_factory() as session:
        for pt in points:
            try:
                was_new = await _upsert_point(session, pt)
                inserted += int(was_new)
                updated += int(not was_new)
            except Exception as exc:
                errors += 1
                logger.error(
                    "macro.upsert_failed",
                    indicator=pt.indicator,
                    date=pt.date.isoformat(),
                    error=str(exc),
                )
        await session.commit()

    await engine.dispose()

    summary = {
        "fetched": len(points),
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
    }
    logger.info("macro.daily_complete", **summary)
    return summary


@celery_app.task(  # type: ignore[misc]
    name="psx_ingest.tasks.macro.ingest_macro_daily",
    bind=True,
    max_retries=3,
    default_retry_delay=600,
)
def ingest_macro_daily(self: object) -> dict[str, int]:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("macro.task_failed", error=str(exc))
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]
