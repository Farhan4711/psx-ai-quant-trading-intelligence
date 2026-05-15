# PSX AI — Remaining Build Plan

**Status:** Steps 1–73 of the original `PSX_WebApp_Build_Plan.md` are
shipped. This file picks up at Step 74 and runs through the genuine
remainder: ~40 incremental steps grouped into 8 phases.

**Design rules** (same as the original plan):

- One step = one runnable, verifiable thing
- Each step has **goal / files / acceptance check** so progress is provable
- Phases are sequenced so each one builds on the last — finish a phase before starting the next
- Steps marked **🚧 GATED** need external resources (GPU rental, cash for hosting) — skip until unblocked

---

## Phase 6 — Local bring-up (must do first)

Goal: have the full stack running on your laptop before building more.

### Step 74 — Install Postgres 16 + Redis 7 locally
- **Goal:** Replace the missing infra so the backend can boot
- **Pick one of:**
  - Docker Desktop + `psx-infra/docker-compose.dev.yml`
  - Native Postgres 16 installer + Memurai (Windows Redis-compatible)
- **Acceptance:** `psql -U psx_user -d psx_dev -c "select 1"` returns `1`, `redis-cli ping` returns `PONG`

### Step 75 — Backend venv + dependencies
- **Goal:** Get Python deps installed without the 3.14 wheel issues
- **Files:** `psx-api/.venv/`, `psx-api/.env`
- **Commands:** `py -3.12 -m venv .venv` → `.venv\Scripts\pip install -e ".[dev]"`
- **Acceptance:** `pytest -x -q` runs (some DB tests may skip without DB — that's fine)

### Step 76 — Apply all 15 migrations
- **Goal:** Materialize the full schema
- **Command:** `alembic upgrade head`
- **Acceptance:** `\dt` in psql lists ~30 tables including `payment_intents`, `subscription_plans`, `lessons`, `notifications`

### Step 77 — End-to-end smoke
- **Goal:** Sign up, log in, record a fake trade, see portfolio dashboard
- **Files:** none (manual click-through)
- **Acceptance:** A user account exists, one trade is recorded, the dashboard shows after-tax P&L without 500-errors

---

## Phase 7 — News scrapers (fills the empty Pulse/sentiment surfaces)

The schema, sentiment scorer, pulse aggregation, and frontend are
already wired. This phase fills the data side.

### Step 78 — Scraper base utilities
- **Goal:** Shared HTTP/dedupe/rate-limit primitives so every source isn't reinventing them
- **Files:** `psx-ingest/psx_ingest/news/base.py` (HTTPX client w/ user-agent + 1 req/sec floor + redis-backed URL dedupe)
- **Acceptance:** A 5-line scraper using `BaseNewsScraper` ingests a fixed sample HTML page into `news_articles`

### Step 79 — Dawn Business scraper
- **Goal:** RSS + page fetch for dawn.com/business
- **Files:** `psx-ingest/psx_ingest/news/sources/dawn.py`
- **Acceptance:** Run `python -m psx_ingest.news.sources.dawn` → ≥5 articles inserted, mentions extracted via existing `aliases_from_securities`

### Step 80 — Business Recorder scraper
- **Files:** `psx-ingest/psx_ingest/news/sources/brecorder.py`
- **Acceptance:** Same as Step 79

### Step 81 — Profit Pakistan Today scraper
- **Files:** `psx-ingest/psx_ingest/news/sources/profit.py`
- **Acceptance:** Same as Step 79

### Step 82 — The News + Tribune scrapers
- **Files:** `psx-ingest/psx_ingest/news/sources/thenews.py`, `tribune.py`
- **Acceptance:** All 5 sources visible in `news_articles.source` distinct values

### Step 83 — Wire scrapers to Celery beat
- **Goal:** 30-min schedule during PSX hours (09:30–15:30 PKT), 6-hr schedule otherwise
- **Files:** `psx-ingest/psx_ingest/celery_app.py` (beat schedule)
- **Acceptance:** `celery -A psx_ingest beat -l info` logs the 5 scheduled tasks

### Step 84 — Macro indicator scrapers
- **Goal:** KIBOR 1m/3m/6m/12m, SBP policy rate, PKR/USD, Brent, gold
- **Files:** `psx-ingest/psx_ingest/macro/sbp.py`, `psx-ingest/psx_ingest/macro/forex.py`
- **Acceptance:** `macro_indicators` table has rows for each of the 8 indicators dated today

---

## Phase 8 — Shared type package

### Step 85 — psx-shared OpenAPI → TypeScript
- **Goal:** Stop ad-hoc interfaces in `psx-web/src/lib/api/*.ts` from drifting
- **Files:**
  - `psx-shared/package.json` (build script using `openapi-typescript`)
  - `psx-shared/openapi.json` (committed snapshot — refreshed by `pnpm gen`)
  - `psx-shared/src/index.ts` (re-exports the generated types)
- **Acceptance:** `pnpm --filter psx-shared gen` regenerates types from a running API; `psx-web` imports `Plan`/`Transaction` from `@psx/shared`

### Step 86 — Replace ad-hoc types in psx-web
- **Goal:** All five `lib/api/*.ts` files use the shared types
- **Files:** every file under `psx-web/src/lib/api/`
- **Acceptance:** `pnpm tsc` passes; deleting `psx-shared/src/index.ts` breaks the build (proves it's actually used)

---

## Phase 9 — Auth hardening

### Step 87 — GET /api/v1/auth/sessions
- **Goal:** List active sessions (device, IP-ish, last-seen, current-flag) for the logged-in user
- **Files:** `psx-api/psx_api/routers/auth.py`, `psx_api/services/auth_service.py`
- **Acceptance:** Logged-in user can fetch their own session list; another user's request returns `[]`

### Step 88 — DELETE /api/v1/auth/sessions/{id}
- **Goal:** Revoke a single session (or "all other sessions")
- **Files:** same router/service
- **Acceptance:** Revoking from device A logs out device B; revoking own session 401s subsequent requests

### Step 89 — Settings → Security tab
- **Goal:** Surface sessions list + revoke buttons + the existing TOTP toggle in one tab
- **Files:** `psx-web/src/app/(app)/settings/page.tsx` (split into Tabs: Profile / Security / Notifications)
- **Acceptance:** User can see their sessions and revoke one from the UI

### Step 90 — Resend verification email
- **Goal:** A user who lost the original email can request another (rate-limited: 1 per 5 min)
- **Files:** `routers/auth.py` (`POST /api/v1/auth/resend-verification`), `app/(auth)/verify-email/page.tsx` ("Didn't get it?" link)
- **Acceptance:** Second request within 5 min returns 429; otherwise email is logged/sent

---

## Phase 10 — Polish & anomaly

### Step 91 — Isolation Forest anomaly trainer
- **Goal:** Replace the placeholder anomaly score in `psx_api/alerts/pump_dump.py` with a per-stock IsolationForest trained on 2 yrs of OHLCV features
- **Files:** `psx-ingest/psx_ingest/anomaly/train.py`, `models/anomaly/{symbol}.joblib`
- **Acceptance:** `python -m psx_ingest.anomaly.train --symbol HBL` writes a model file; `AlertService.evaluate_today("HBL")` uses it (verified via mocking)

### Step 92 — peer_aggregates nightly Celery task
- **Goal:** Compute anonymous benchmarking buckets nightly so the read path actually returns data
- **Files:** `psx-ingest/psx_ingest/benchmark/aggregate.py` (Celery task using `psx_api/benchmark/buckets.py`)
- **Acceptance:** With 5+ opted-in fake users, task writes rows to `peer_aggregates`; suppression at <5 still works

### Step 93 — Lessons seed migration
- **Goal:** Move `LessonService.seed_curriculum()` out of a one-off API call and into a migration
- **Files:** `alembic/versions/0016_seed_lessons.py` (bulk_insert from `psx_api.learning.curriculum`)
- **Acceptance:** Fresh DB after `alembic upgrade head` has all 10 lessons populated

### Step 94 — Dashboard widgets
- **Goal:** Replace the 4-tile placeholder with portfolio value, market movers, watchlist snapshot, recent alerts
- **Files:** `psx-web/src/app/(app)/dashboard/page.tsx`, new server components for each widget
- **Acceptance:** Logged-in user lands on a dashboard that shows real data for their portfolio + watchlist

### Step 95 — Settings → Notifications tab
- **Goal:** Toggle which notification kinds the user wants (pump/dump, KMI changes, weekly summary, payment events)
- **Files:** `psx-api/psx_api/models/users.py` (`notification_prefs` JSONB col), migration 0017, settings page
- **Acceptance:** Toggles persist; `NotificationService.send()` honours the prefs

---

## Phase 11 — CI & ops hygiene

### Step 96 — Weekly security scan in CI
- **Goal:** Wire `scripts/security-scan.sh` to run on a weekly schedule in GitHub Actions, gate merges on critical findings
- **Files:** `.github/workflows/security-scan.yml`
- **Acceptance:** The workflow appears in Actions tab; manual trigger runs and uploads logs as an artifact

### Step 97 — Local Lighthouse + a11y pass
- **Goal:** Top 5 pages hit Performance ≥90, Accessibility ≥95 on desktop and mobile profiles
- **Files:** none (audit + fixes in existing components)
- **Acceptance:** Lighthouse report PDF in `psx-docs/audits/lighthouse-YYYY-MM-DD.pdf` showing scores

---

## Phase 12 — Real ML models 🚧 GATED (need GPU)

Rent a GPU on RunPod / Lambda Cloud for a weekend (~$15) when you're ready.

### Step 98 — Training data extraction
- **Goal:** Pull (symbol × date × 25 features × y_next_day_up) from the DB into a parquet file
- **Files:** `psx-inference/training/extract.py`
- **Acceptance:** A parquet file with N rows where N ≈ 84 symbols × ~1250 trading days

### Step 99 — XGBoost trainer (per stock)
- **Files:** `psx-inference/training/train_xgb.py` (one model per symbol; classification, AUC > 0.55 to pass)
- **Acceptance:** `models/xgb/{symbol}.json` files for each passing symbol

### Step 100 — Random Forest trainer
- **Files:** `psx-inference/training/train_rf.py`
- **Acceptance:** Same as Step 99, `models/rf/{symbol}.joblib`

### Step 101 — LSTM / 1D-CNN trainer
- **Goal:** 60-day window, PyTorch, early stopping on validation AUC
- **Files:** `psx-inference/training/train_lstm.py`, `models/lstm/{symbol}.pt`
- **Acceptance:** Same as Step 99 with PyTorch checkpoints

### Step 102 — Stacking meta-model
- **Goal:** Logistic regression on top of the 3 sub-model outputs
- **Files:** `psx-inference/training/train_meta.py`, `models/meta/{symbol}.joblib`
- **Acceptance:** Meta AUC ≥ best sub-model AUC

### Step 103 — ONNX export
- **Goal:** Export all 4 model layers (XGB/RF/LSTM/meta) to ONNX so inference is framework-agnostic
- **Files:** `psx-inference/training/export_onnx.py`, `models/onnx/{symbol}.onnx`
- **Acceptance:** ONNX Runtime can load each `.onnx` file and produce a probability for a sample input

### Step 104 — Inference service ONNX loader
- **Goal:** Replace the TODO in `psx_inference/main.py` lifespan hook with actual model loading
- **Files:** `psx-inference/psx_inference/main.py`, `psx-inference/psx_inference/inference.py`
- **Acceptance:** `POST /predict` against the running service returns probability + confidence + top-3 feature contributions, in <100ms p95

### Step 105 — Swap heuristic ensemble for real models
- **Goal:** `psx_api/predictions/ensemble.py` becomes a thin client of `psx-inference`
- **Files:** `psx_api/predictions/ensemble.py` (single-file change per the original plan note)
- **Acceptance:** `PredictionService.predict("HBL")` calls inference service; live accuracy of real models tracked in `model_predictions`

### Step 106 — Monthly retrain task + quality gate
- **Goal:** Per-stock auto-disable when live accuracy drops below 53% over the last 60 predictions
- **Files:** `psx-ingest/psx_ingest/predictions/retrain.py` (Celery beat: 1st of month, 02:00 PKT), DB flag on `securities` for `predictions_disabled`
- **Acceptance:** A symbol that loses the gate gets a `predictions_disabled` row and the UI renders the existing disabled state

---

## Phase 13 — Production launch 🚧 GATED (need cash for hosting)

### Step 107 — Hetzner provisioning
- **Goal:** CCX23 + Cloudflare DNS + R2 bucket, per `DEPLOYMENT.md`
- **Acceptance:** `ssh deploy@psxai.example` works; `docker version` runs

### Step 108 — Production env + secrets
- **Goal:** `.env.prod` populated with real secrets (SECRET_KEY, SMTP, Sentry DSN, R2 keys, gateway creds)
- **Acceptance:** `docker-compose --env-file .env.prod config` validates with no missing vars

### Step 109 — First deploy + DB seed
- **Goal:** `release-vX.Y.Z` tag triggers GHA release workflow → containers land on prod → `alembic upgrade head` → securities seeded
- **Acceptance:** `curl https://api.psxai.example/health` returns `{"ok": true}`

### Step 110 — Domain + TLS
- **Goal:** Caddy auto-provisions Let's Encrypt; HSTS + headers verified by `scripts/security-scan.sh PROD_URL=https://psxai.example`
- **Acceptance:** All 3 security headers present; SSL Labs grade A

### Step 111 — Backups + monitoring
- **Goal:** Nightly pg_dump → R2 (30-day retention); BetterStack uptime monitor; Grafana panels for signups/day, trades/day, predictions/day
- **Acceptance:** Tomorrow's backup is in R2; uptime monitor reports green; Grafana shows non-zero metrics

### Step 112 — Soft launch
- **Goal:** Invite ~20 testers, monitor Sentry + Grafana for a week, fix anything that breaks
- **Acceptance:** Zero P0 issues for 7 consecutive days → flip the marketing site live and start public signups

---

## Suggested execution order

1. **Today:** Phase 6 (Steps 74–77) — get it running
2. **Next session:** Phase 7 (78–84) — news scrapers, biggest UX impact
3. **Then:** Phase 8 (85–86) — shared types, prevents future drift
4. **Then:** Phase 9 (87–90) — auth hardening, real security win
5. **Then:** Phase 10 (91–95) — polish + the dashboard finally looks alive
6. **Then:** Phase 11 (96–97) — CI hygiene, one-time setup
7. **When budget allows GPU rental:** Phase 12 (98–106)
8. **When budget allows hosting:** Phase 13 (107–112)

Phases 6–11 are **38 steps, all laptop-only, no recurring costs.** Doing them in
order is the cheapest way to get a real, end-to-end working product.
