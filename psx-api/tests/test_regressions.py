"""
Regression tests for bugs found in the post-Phase-4 audit.

Each test pins a specific bug to a behaviour so it doesn't sneak back
when refactors touch the related code.
"""

from __future__ import annotations

import pytest

from psx_api.services.notification_service import VALID_KINDS

# ── R-001: notification kind whitelist ─────────────────────────────────
#
# The Phase 4 audit (migration 0011) created the `notifications` table
# without a CHECK constraint on `kind`, even though the schema comment
# documented exactly 4 valid values. Code paths that read notifications
# (the NotificationsBell UI) assume kind is one of those 4, so an INSERT
# with an unknown kind silently breaks rendering.
#
# Fix: migration 0012 adds the CHECK + NotificationService.send() now
# validates against VALID_KINDS *before* the INSERT for a clean
# ValueError instead of an IntegrityError surfaced at flush time.


class TestNotificationKindWhitelist:
    def test_valid_kinds_constant_matches_migration(self) -> None:
        # If migration 0012 ever changes the whitelist, this test breaks
        # and the constant must be updated alongside.
        assert VALID_KINDS == frozenset({"kmi_delisting", "pump_dump", "goal_milestone", "system"})

    def test_unknown_kind_is_a_value_error_not_db_error(self) -> None:
        # Importable without a DB connection — the validation lives in
        # the service layer so we don't even need to mock AsyncSession.
        from psx_api.services.notification_service import NotificationService

        service = NotificationService(db=None)  # type: ignore[arg-type]

        # `send()` is async; we just check that the validation raises
        # synchronously before any await on the DB.
        import asyncio

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                service.send(
                    user_id="00000000-0000-0000-0000-000000000000",
                    kind="not_a_real_kind",
                    title="ignored",
                    body="ignored",
                )
            )
        assert "Unknown notification kind" in str(exc_info.value)
        for k in VALID_KINDS:
            assert k in str(exc_info.value)


# ── R-002: structlog public API ────────────────────────────────────────
#
# main.py was using `structlog.stdlib._NAME_TO_LEVEL` (private, leading
# underscore) which was removed in modern structlog versions. The
# correct public name is `NAME_TO_LEVEL`. Importing `psx_api.main`
# blew up with AttributeError on any non-stale structlog install.


class TestStructlogPublicAPI:
    def test_imports_main_without_attribute_error(self) -> None:
        # If the private-name access regresses, this fails at import.
        import psx_api.main  # noqa: F401

    def test_uses_public_name_to_level(self) -> None:
        import structlog.stdlib

        # The public attribute exists in supported structlog versions.
        # If structlog removes it again, our code path falls back to
        # INFO=20 thanks to getattr(..., {}).get(..., 20).
        assert hasattr(structlog.stdlib, "NAME_TO_LEVEL")


# ── R-003: lazy DB engine ──────────────────────────────────────────────
#
# Before the fix, importing psx_api.database constructed an AsyncEngine
# pointing at `settings.database_url` — which failed any time the DB
# URL pointed at a host the importing process couldn't reach (CI
# without Postgres, pure-module test runs, OpenAPI introspection in
# isolation). Now the engine is lazy.


class TestLazyDatabaseEngine:
    def test_module_imports_cleanly(self) -> None:
        import psx_api.database  # noqa: F401

    def test_get_engine_idempotent(self) -> None:
        from psx_api.database import get_engine

        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2  # one engine for the life of the process

    def test_compat_shim_exposes_engine_attr(self) -> None:
        """Old code that does `from psx_api.database import engine` must still work."""
        from psx_api import database

        # Attribute access triggers __getattr__ → returns the lazy engine
        assert database.engine is not None
        assert database.AsyncSessionLocal is not None
