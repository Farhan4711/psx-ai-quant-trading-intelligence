# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk
# Internal reference: psx-docs/adr/ADR-000-psx-data-licensing.md

import sentry_sdk
from celery import Celery
from celery.schedules import crontab
from sentry_sdk.integrations.celery import CeleryIntegration

from psx_ingest.config import settings

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[CeleryIntegration()],
        traces_sample_rate=0.05,
        send_default_pii=False,
    )

celery_app = Celery(
    "psx_ingest",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["psx_ingest.tasks.ohlcv", "psx_ingest.tasks.backfill", "psx_ingest.tasks.corporate_actions"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Karachi",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry failed tasks up to 3 times with exponential backoff
    task_max_retries=3,
    task_default_retry_delay=60,
)

# Beat schedule — all times in PKT (Asia/Karachi)
celery_app.conf.beat_schedule = {
    # Daily EOD ingestion — runs at 4:45 PM PKT (market closes at 3:30 PM + buffer)
    "ingest-eod-ohlcv": {
        "task": "psx_ingest.tasks.ohlcv.ingest_eod_ohlcv",
        "schedule": crontab(hour=16, minute=45),
    },
    # Corporate actions — scrape PUCARS twice daily
    "ingest-corporate-actions-morning": {
        "task": "psx_ingest.tasks.corporate_actions.ingest_corporate_actions",
        "schedule": crontab(hour=9, minute=0),
    },
    "ingest-corporate-actions-evening": {
        "task": "psx_ingest.tasks.corporate_actions.ingest_corporate_actions",
        "schedule": crontab(hour=17, minute=30),
    },
}
