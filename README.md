# PSX AI Quant Trading Intelligence

A responsive, mobile-first web application for Pakistan Stock Exchange (PSX) retail investors — combining portfolio tracking, technical/fundamental analysis, ML-based price predictions with honest confidence labeling, backtesting, anomaly detection, news sentiment, and Shariah-compliance tooling.

## Repository Structure

This is a **monorepo**. Each top-level directory maps to a logical service:

| Directory | Purpose |
|---|---|
| [`psx-web/`](./psx-web/) | Next.js 14+ App Router frontend |
| [`psx-api/`](./psx-api/) | FastAPI main backend (auth, portfolio, analytics) |
| [`psx-ingest/`](./psx-ingest/) | Data ingestion workers (EOD prices, corporate actions, news) |
| [`psx-inference/`](./psx-inference/) | ML model training and ONNX inference microservice |
| [`psx-shared/`](./psx-shared/) | Shared TypeScript types + Python Pydantic models |
| [`psx-infra/`](./psx-infra/) | Docker Compose, CI/CD, deployment configs |
| [`psx-docs/`](./psx-docs/) | ADRs, runbooks, legal docs, email templates |

## Tech Stack

- **Frontend:** Next.js 14+, TypeScript (strict), TailwindCSS, shadcn/ui, TanStack Query, Zustand, TradingView Lightweight Charts, ECharts, Auth.js v5
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Celery + Redis
- **Database:** PostgreSQL 15+ with TimescaleDB extension, Redis 7+
- **ML:** scikit-learn, XGBoost, PyTorch, pandas-ta, vectorbt, ONNX Runtime
- **Infra:** Docker, GitHub Actions, Hetzner Cloud, Cloudflare, Sentry, Grafana, Prometheus

## Build Status

| Service | Lint | Tests | Build |
|---|---|---|---|
| psx-api | ![lint](https://github.com/Farhan4711/psx-ai-quant-trading-intelligence/actions/workflows/api-ci.yml/badge.svg) | — | — |
| psx-web | ![lint](https://github.com/Farhan4711/psx-ai-quant-trading-intelligence/actions/workflows/web-ci.yml/badge.svg) | — | — |
| psx-ingest | ![lint](https://github.com/Farhan4711/psx-ai-quant-trading-intelligence/actions/workflows/ingest-ci.yml/badge.svg) | — | — |
| psx-inference | ![lint](https://github.com/Farhan4711/psx-ai-quant-trading-intelligence/actions/workflows/inference-ci.yml/badge.svg) | — | — |

## Development Setup

See each service's README for local setup instructions:
- [psx-api — Backend setup](./psx-api/README.md)
- [psx-web — Frontend setup](./psx-web/README.md)
- [psx-ingest — Ingest workers setup](./psx-ingest/README.md)
- [psx-infra — Docker Compose full-stack](./psx-infra/README.md)

## Data Licensing

PSX market data is used under an educational/non-commercial arrangement.
See [`psx-docs/adr/ADR-000-psx-data-licensing.md`](./psx-docs/adr/ADR-000-psx-data-licensing.md)
and [`psx-ingest/LICENSING_NOTICE.md`](./psx-ingest/LICENSING_NOTICE.md).

## Documentation

- [Architecture Decision Records](./psx-docs/adr/)
- [Runbooks](./psx-docs/runbooks/)
- [Legal](./psx-docs/legal/)
