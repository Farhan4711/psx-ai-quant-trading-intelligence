# Testing the PSX AI Trading System

A guide for getting from a fresh clone to a green test suite + a running app.

---

## Quick test run (just the pure-module tests, no infra)

If you only want to verify the math (tax engine, indicators, backtest,
predictions, news pulse, purification, etc.) — these have no DB / Redis
dependency:

```sh
cd psx-api
python -m pip install -e ".[dev]"        # full deps (see Python-version note)
python -m pytest tests/                  # 137/137 should pass
```

Frontend type-check + unit tests:

```sh
cd psx-web
pnpm install
pnpm type-check                          # tsc --noEmit, clean
pnpm test                                # vitest, 6/6
```

**That's the bar this repo holds.** Everything below assumes you want to
exercise the full app end-to-end.

---

## Python version

The backend pins specific package versions in `pyproject.toml`. Some of
those packages — notably **asyncpg** and **pydantic-core** — ship prebuilt
wheels for Python 3.11/3.12/3.13 only. **Python 3.14 will fail to install**
without a C compiler.

**Recommended**: Python **3.12** in a venv. If you're on 3.14 (current
default on some Windows machines), either:

1. Install Python 3.12 alongside ([python.org](https://www.python.org/downloads/release/python-3127/)) and create a venv:
   ```sh
   cd psx-api
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
2. Or accept that asyncpg won't install — the pure-Python tests still
   run on 3.14 because we made `psx_api.database` lazy-init the engine.
   Most of the backend's test value is in the pure modules; you only
   need Postgres for integration tests.

---

## Full stack run (Postgres + Redis + backend + frontend)

### Prerequisites

- **Docker Desktop** (free for personal use) for the dev stack — OR —
- Native installs of Postgres 16 and Redis 7

### Bring up infra (Docker Desktop path)

A `docker-compose.dev.yml` for local dev isn't shipped yet, so the
simplest path is two commands:

```sh
docker run -d --name psx-postgres -e POSTGRES_USER=psx_user -e POSTGRES_PASSWORD=psx_pass -e POSTGRES_DB=psx_dev -p 5432:5432 postgres:16-alpine
docker run -d --name psx-redis -p 6379:6379 redis:7-alpine
```

### Backend

```sh
cd psx-api
cp .env.example .env                     # then set SECRET_KEY: openssl rand -hex 32
alembic upgrade head                     # runs all 12 migrations
uvicorn psx_api.main:app --reload --port 8000
```

OpenAPI docs at <http://localhost:8000/api/docs>.

### Frontend

```sh
cd psx-web
cp .env.example .env.local 2>/dev/null   # if you have one; otherwise NEXT_PUBLIC_API_URL=http://localhost:8000 is enough
pnpm dev
```

Visit <http://localhost:3000>.

### Smoke test

1. **Sign up** at /signup → fill the form
2. **Verify email** — in dev the verification email isn't actually sent;
   check the backend log for the token, then visit `/verify-email?token=...`
3. **Log in** → dashboard
4. **Browse /app/stocks** → click a symbol → see chart + signal panel
5. **Watchlist** → add a stock → reorder
6. **Portfolio** → record a buy + a sell, see the FIFO matched lots
   and CGT computed in the confirmation step
7. **Risk Profile** → take the 12-question quiz → see your archetype
8. **Goals** → add a Hajj goal → see required CAGR
9. **Lessons** → POST `/api/v1/lessons/seed` once (admin endpoint, no auth)
   to load the 10 starter lessons, then visit `/app/lessons`
10. **Tax simulator** → after logging a sell, see the filer-vs-non-filer delta
11. **Backtest** → pick a symbol with OHLCV history, run a strategy

---

## Where the data comes from

The app expects **securities** and **OHLCV history** to be pre-loaded.
The ingestion pipeline lives in `psx-ingest/` (not yet wired into this
walkthrough). Without it, most pages will look empty.

For a quick smoke test, you can manually insert a handful of symbols + a
year of OHLCV via psql. A demo seed script is on the wishlist (see
"quick wins" in the project plan).

---

## What's covered by automated tests

| Suite | File | Count | Scope |
|---|---|---|---|
| Tax engine | `test_tax_cgt.py` | 24 | CGT rates, FIFO matching, edge cases |
| Phase 2A | `test_phase2a.py` | 17 | Risk profile, TVM, allocation |
| Backtest | `test_backtest.py` | 13 | Engine, 5 strategies, metrics, narration |
| Phase 2C | `test_phase2c.py` | 12 | Feature pipeline, heuristic ensemble |
| Phase 3 | `test_phase3.py` | 23 | News extract / sentiment / pulse, pump/dump |
| Phase 4 | `test_phase4.py` | 22 | Buckets, strategy parser, purification, lessons |
| Health + Auth | `test_health.py` + `test_auth.py` | 26 | Endpoint integration via httpx ASGI client |
| **Total** | | **137** | |

Coverage is heaviest on the **pure-math modules** (the things where a
silent bug would directly leak money — tax, FIFO matching, TVM, indicators).
Coverage is **lighter on the service layer** — that's the next reasonable
testing target if you want to invest more in safety.

---

## Known limitations / what won't work without infra

1. **News scrapers**: schema is ready, the per-source fetchers are not
   implemented (`psx-ingest/scrapers/dawn_business.py` etc.). News Pulse
   will show "no tagged news" until articles exist.

2. **Live KMI delisting alerts**: the notification primitives ship, the
   cron that detects KMI membership changes does not.

3. **Real ML models**: the prediction service ships a deterministic
   heuristic ensemble (`MODEL_VERSION="heuristic-v0.1.0"`). Real LSTM/
   XGBoost/RandomForest training + ONNX serving is documented in
   `psx_api/predictions/RETRAINING.md` but not wired up.

4. **Benchmark aggregation cron**: peer_aggregates table is ready, the
   nightly batch is not. The /app/portfolio "How I compare" panel will
   show "need 5+ peers" until aggregation runs.

5. **Email sending**: signup verification + password reset use
   `aiosmtplib`; in dev with no SMTP config the email contents log to
   stdout instead of sending.

6. **Sentry**: only initialised when `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN`
   are set, so dev runs cleanly without Sentry credentials.

---

## Reporting bugs

Add a regression test in the appropriate `test_*.py`, then file the bug.
The repo's been kept honest by tests — keep the bar high.
