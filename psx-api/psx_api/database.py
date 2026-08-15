"""
DB engine + session factory.

Lazy-initialised: the engine is only built on the first call to `get_engine()`
or `get_session_factory()`. This matters because:

  1. Test runs that exercise pure modules (psx_api.tax, psx_api.indicators,
     psx_api.backtest, etc.) shouldn't require a working Postgres URL — many
     CI jobs run without a DB.
  2. Importing `psx_api.main` for OpenAPI introspection shouldn't bind to
     Postgres credentials that may not exist in the importing context.
  3. Tests can override `get_db` via FastAPI's `dependency_overrides` (see
     tests/conftest.py) before any engine is built.

The same engine instance is reused for the life of the process once built.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from psx_api.config import settings

if TYPE_CHECKING:
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Compatibility shims ────────────────────────────────────────────────
# Some callers still import `engine` / `AsyncSessionLocal` directly. Resolve
# lazily on attribute access so the engine isn't built at import time.


def __getattr__(name: str) -> AsyncEngine | async_sessionmaker[AsyncSession]:
    if name == "engine":
        return get_engine()
    if name == "AsyncSessionLocal":
        return get_session_factory()
    raise AttributeError(f"module 'psx_api.database' has no attribute {name!r}")
