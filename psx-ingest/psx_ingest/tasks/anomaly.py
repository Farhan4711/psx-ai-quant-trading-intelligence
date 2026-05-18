"""
Nightly anomaly-model trainer Celery task.

Runs at 02:30 PKT — well clear of the EOD ingest (16:45) and macro
scrape (17:00), so by the time training starts the previous day's
OHLCV is already in `ohlcv_daily`.
"""

from __future__ import annotations

import asyncio

import structlog

from psx_ingest.anomaly.train import summary_as_dict, train_all
from psx_ingest.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(  # type: ignore[misc]
    name="psx_ingest.tasks.anomaly.train_anomaly_models",
    bind=True,
    max_retries=2,
    default_retry_delay=900,
)
def train_anomaly_models(self: object) -> dict[str, int]:
    try:
        summary = asyncio.run(train_all())
        return summary_as_dict(summary)
    except Exception as exc:
        logger.error("anomaly.task_failed", error=str(exc))
        raise self.retry(exc=exc)  # type: ignore[attr-defined]
