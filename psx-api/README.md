# psx-api — FastAPI Main Backend

Core API service: authentication, portfolio management, stock data serving, technical indicators, tax engine.

## Tech Stack

- **Framework:** FastAPI (Python 3.11+)
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Background jobs:** Celery + Redis
- **Password hashing:** Argon2id (argon2-cffi)
- **Testing:** pytest + httpx (async test client)
- **Linting:** ruff, mypy (strict)

## Prerequisites

- Python 3.11+
- PostgreSQL 15 with TimescaleDB extension (or use Docker Compose from `../psx-infra/`)
- Redis 7+
- uv (recommended: `pip install uv`) or pip

## Local Setup

```bash
cd psx-api
cp .env.example .env
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn psx_api.main:app --reload --port 8000
```

API docs at http://localhost:8000/api/docs
ReDoc at http://localhost:8000/api/redoc

## Scripts

| Command | Description |
|---|---|
| `uvicorn psx_api.main:app --reload` | Start dev server |
| `pytest` | Run all tests |
| `pytest --cov=psx_api --cov-report=html` | Tests with coverage |
| `ruff check .` | Lint |
| `ruff format .` | Format |
| `mypy psx_api/` | Type check |
| `alembic upgrade head` | Apply all migrations |
| `alembic revision --autogenerate -m "description"` | Generate migration |

## Directory Structure (to be created in Phase 1)

```
psx-api/
├── psx_api/
│   ├── main.py                 # FastAPI app factory
│   ├── config.py               # Settings via pydantic-settings
│   ├── database.py             # SQLAlchemy async engine + session
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic v2 request/response schemas
│   ├── routers/                # FastAPI routers (one per domain)
│   │   ├── auth.py
│   │   ├── securities.py
│   │   ├── portfolio.py
│   │   ├── watchlist.py
│   │   └── indicators.py
│   ├── services/               # Business logic (no FastAPI deps)
│   │   ├── auth_service.py
│   │   ├── indicator_service.py
│   │   └── tax/
│   │       └── cgt.py
│   ├── workers/                # Celery tasks
│   └── middleware/
├── alembic/
│   ├── versions/
│   └── env.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── pyproject.toml
└── .env.example
```
