"""
News ingestion Celery task — one task per source.

Why per-source instead of one big task
--------------------------------------
- If Dawn's feed is down, we don't want it to block Tribune.
- Different sources move at different cadences (Brecorder updates
  more often than Profit) so it's nice to give them independent
  schedules later if we want.
- Celery's `task_acks_late = True` (set globally in worker.py) means
  a hung HTTP fetch on one source can be killed without losing the
  other four.

Beat schedule (registered in worker.py)
---------------------------------------
- During PSX hours (09:30–15:30 PKT, Mon–Fri): every 30 minutes
- After hours / weekends: every 6 hours

The cron split keeps Redis dedupe + DB-unique URL doing their job
while still being responsive when prices are moving.
"""

from __future__ import annotations

import asyncio
from typing import Any

import redis.asyncio as redis_async
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.config import settings
from psx_ingest.news.base import BaseNewsScraper
from psx_ingest.news.persistence import (
    IngestSummary,
    ingest_article,
    load_alias_index,
)
from psx_ingest.news.sources import (
    BusinessRecorderScraper,
    DawnBusinessScraper,
    ProfitPakistanTodayScraper,
    TheNewsBusinessScraper,
    TribuneBusinessScraper,
)
from psx_ingest.worker import celery_app

logger = structlog.get_logger(__name__)


async def _run_one_source(scraper_cls: type[BaseNewsScraper]) -> dict[str, int]:
    """Run a single scraper end-to-end: fetch feed → fetch articles →
    persist with mentions + sentiment. Returns the summary dict."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis_client = redis_async.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url, encoding="utf-8", decode_responses=True
    )

    summary = IngestSummary()
    try:
        async with session_factory() as session:
            aliases = await load_alias_index(session)
            if not aliases:
                logger.warning(
                    "news.no_aliases",
                    scraper=scraper_cls.source_slug,
                )

        async with scraper_cls(redis=redis_client) as scraper:
            async with session_factory() as session:
                async for article in scraper.fetch_articles():
                    await ingest_article(session, article, aliases, summary)
                await session.commit()
    finally:
        await redis_client.close()
        await engine.dispose()

    logger.info(
        "news.source_complete",
        source=scraper_cls.source_slug,
        **summary.as_dict(),
    )
    return summary.as_dict()


def _make_task(scraper_cls: type[BaseNewsScraper]) -> Any:
    """Factory so each source gets its own Celery task name + retry policy."""

    @celery_app.task(  # type: ignore[misc]
        name=f"psx_ingest.tasks.news.scrape_{scraper_cls.source_slug}",
        bind=True,
        max_retries=2,
        default_retry_delay=120,
    )
    def _task(self: object) -> dict[str, int]:
        try:
            return asyncio.run(_run_one_source(scraper_cls))
        except Exception as exc:
            logger.error(
                "news.task_failed",
                scraper=scraper_cls.source_slug,
                error=str(exc),
            )
            raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]

    return _task


# Bind a task per source so beat can target each independently.
scrape_dawn = _make_task(DawnBusinessScraper)
scrape_brecorder = _make_task(BusinessRecorderScraper)
scrape_profit = _make_task(ProfitPakistanTodayScraper)
scrape_thenews = _make_task(TheNewsBusinessScraper)
scrape_tribune = _make_task(TribuneBusinessScraper)
