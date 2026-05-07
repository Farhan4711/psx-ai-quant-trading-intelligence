# psx-ingest — Data Ingestion Workers

Celery workers responsible for: EOD OHLCV ingestion, corporate actions scraping,
news article collection, and macro indicator ingestion.

> **IMPORTANT — Read before touching any file in this directory:**
> [`LICENSING_NOTICE.md`](./LICENSING_NOTICE.md)

## Tech Stack

- Python 3.11+, Celery + Redis
- httpx (async HTTP), BeautifulSoup4 (HTML parsing)
- pandas, pandas-ta
- SQLAlchemy 2.0 (shared models from psx-api)

## Prerequisites

Same as `psx-api` — shares the same database. Run from `../psx-infra/` with Docker Compose.

## Local Setup

```bash
cd psx-ingest
cp .env.example .env
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
# Start workers
celery -A psx_ingest.worker worker --loglevel=info
# Start beat scheduler (cron-like triggers)
celery -A psx_ingest.worker beat --loglevel=info
```

## Directory Structure (to be created in Phase 1)

```
psx-ingest/
├── psx_ingest/
│   ├── worker.py               # Celery app factory + beat schedule
│   ├── tasks/
│   │   ├── ohlcv.py            # Daily EOD ingestion from DPS
│   │   ├── corporate_actions.py # PUCARS scraper
│   │   ├── adjusted_prices.py  # Split/dividend adjustment computation
│   │   └── macro.py            # KIBOR, SBP rate, PKR/USD, oil, gold
│   ├── scrapers/               # Phase 3: news scrapers
│   │   ├── dawn_business.py
│   │   ├── business_recorder.py
│   │   └── ...
│   └── validators.py           # Data integrity checks
├── tests/
├── pyproject.toml
└── .env.example
```

## Rate Limiting Policy

All HTTP requests to external sources must:
- Wait ≥ 3 seconds between requests to the same domain
- Run heavy backfill during off-peak (midnight–6 AM PKT)
- Respect `robots.txt`
- Archive raw responses to object storage before parsing

See `LICENSING_NOTICE.md` for full policy.
