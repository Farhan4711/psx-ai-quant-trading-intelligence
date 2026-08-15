"""
Nightly peer-aggregate Celery task.

Scheduled at 03:30 PKT — after the anomaly trainer finishes around
02:30, so the queue isn't double-loaded.
"""

from __future__ import annotations

import asyncio

import structlog

from psx_ingest.benchmark.aggregate import run_aggregation
from psx_ingest.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(  # type: ignore[misc]
    name="psx_ingest.tasks.benchmark.aggregate_peer_buckets",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def aggregate_peer_buckets(self: object) -> dict[str, int]:
    try:
        summary = asyncio.run(run_aggregation())
        return summary.as_dict()
    except Exception as exc:
        logger.error("benchmark.task_failed", error=str(exc))
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]
