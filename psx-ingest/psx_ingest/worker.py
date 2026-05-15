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
    include=[
        "psx_ingest.tasks.ohlcv",
        "psx_ingest.tasks.backfill",
        "psx_ingest.tasks.corporate_actions",
        "psx_ingest.tasks.adjust_prices",
        "psx_ingest.tasks.news",
        "psx_ingest.tasks.macro",
    ],
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
    # Adjusted-price recompute — runs after the evening corporate-actions ingest
    "recompute-adjusted-prices": {
        "task": "psx_ingest.tasks.adjust_prices.recompute_adjusted_prices",
        "schedule": crontab(hour=18, minute=0),
    },
    # ── News scrapers ────────────────────────────────────────────
    # Active hours (09:30-15:30 PKT, Mon-Fri): every 30 minutes.
    # Off-hours: every 6 hours so we still pick up evening/weekend news.
    # Both windows fire from the same task names — Redis URL dedupe and
    # the news_articles.url UNIQUE constraint mean re-runs are no-ops.
    "scrape-dawn-market-hours": {
        "task": "psx_ingest.tasks.news.scrape_dawn",
        "schedule": crontab(minute="0,30", hour="9-15", day_of_week="mon-fri"),
    },
    "scrape-dawn-offhours": {
        "task": "psx_ingest.tasks.news.scrape_dawn",
        "schedule": crontab(minute=15, hour="0,6,18,22"),
    },
    "scrape-brecorder-market-hours": {
        "task": "psx_ingest.tasks.news.scrape_brecorder",
        "schedule": crontab(minute="5,35", hour="9-15", day_of_week="mon-fri"),
    },
    "scrape-brecorder-offhours": {
        "task": "psx_ingest.tasks.news.scrape_brecorder",
        "schedule": crontab(minute=20, hour="0,6,18,22"),
    },
    "scrape-profit-market-hours": {
        "task": "psx_ingest.tasks.news.scrape_profit",
        "schedule": crontab(minute="10,40", hour="9-15", day_of_week="mon-fri"),
    },
    "scrape-profit-offhours": {
        "task": "psx_ingest.tasks.news.scrape_profit",
        "schedule": crontab(minute=25, hour="0,6,18,22"),
    },
    "scrape-thenews-market-hours": {
        "task": "psx_ingest.tasks.news.scrape_thenews",
        "schedule": crontab(minute="15,45", hour="9-15", day_of_week="mon-fri"),
    },
    "scrape-thenews-offhours": {
        "task": "psx_ingest.tasks.news.scrape_thenews",
        "schedule": crontab(minute=30, hour="0,6,18,22"),
    },
    "scrape-tribune-market-hours": {
        "task": "psx_ingest.tasks.news.scrape_tribune",
        "schedule": crontab(minute="20,50", hour="9-15", day_of_week="mon-fri"),
    },
    "scrape-tribune-offhours": {
        "task": "psx_ingest.tasks.news.scrape_tribune",
        "schedule": crontab(minute=35, hour="0,6,18,22"),
    },
    # ── Macro indicators ─────────────────────────────────────────
    # SBP / KIBOR / FX update once a day at 17:00 PKT — these are
    # published as daily snapshots, no need to poll more often.
    "ingest-macro-daily": {
        "task": "psx_ingest.tasks.macro.ingest_macro_daily",
        "schedule": crontab(hour=17, minute=0),
    },
}
