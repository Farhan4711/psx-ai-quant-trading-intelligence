"""
Tests for the new auth surface (Phase 9 Steps 87-90):
- list_sessions / revoke_session / revoke_other_sessions
- resend_verification_email rate-limit
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from psx_api.models.users import User, UserSession
from psx_api.services.auth_service import AuthError, AuthService, _sha256


def _user(**kw: object) -> User:
    defaults = {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "ali@example.pk",
        "email_verified_at": None,
    }
    defaults.update(kw)
    u = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(u, k, v)
    return u  # type: ignore[return-value]


def _session(
    user_id: str, token: str, *, sid: str = "session-1", expired: bool = False
) -> UserSession:
    s = MagicMock(spec=UserSession)
    s.id = sid
    s.user_id = user_id
    s.token_hash = _sha256(token)
    s.user_agent = "Mozilla/5.0 (Macintosh; Chrome/130) Safari/537"
    s.ip_address = "203.0.113.1"
    now = datetime.now(tz=timezone.utc)
    s.created_at = now - timedelta(hours=1)
    s.expires_at = now - timedelta(minutes=1) if expired else now + timedelta(days=30)
    return s  # type: ignore[return-value]


def _make_service(rows: list[UserSession]) -> tuple[AuthService, AsyncMock]:
    """Build an AuthService whose `db.execute().scalars().all()` returns `rows`
    for list-style queries and `.scalar_one_or_none()` returns rows[0] for
    single-row queries."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = rows[0] if rows else None

    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    redis = AsyncMock()
    service = AuthService(db=db, redis=redis)
    return service, db


# ── list_sessions ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_marks_current() -> None:
    user = _user()
    current = _session(user.id, "raw-token", sid="current")
    other = _session(user.id, "other-token", sid="other")
    service, _ = _make_service([current, other])

    out = await service.list_sessions(user, "raw-token")
    by_id = {s["id"]: s for s in out}
    assert by_id["current"]["is_current"] is True
    assert by_id["other"]["is_current"] is False
    # Sensitive fields are stringified — IP is a str, not an INET object.
    assert isinstance(by_id["current"]["ip_address"], str)


@pytest.mark.asyncio
async def test_list_sessions_no_current_token_marks_none() -> None:
    user = _user()
    s = _session(user.id, "any")
    service, _ = _make_service([s])
    out = await service.list_sessions(user, current_raw_token=None)
    assert out[0]["is_current"] is False


# ── revoke_session ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_session_returns_was_current_true() -> None:
    user = _user()
    target = _session(user.id, "raw", sid="abc")
    service, db = _make_service([target])

    revoked, was_current = await service.revoke_session(user, "abc", "raw")
    assert revoked is True
    assert was_current is True
    db.delete.assert_awaited_once_with(target)


@pytest.mark.asyncio
async def test_revoke_session_other_token_not_current() -> None:
    user = _user()
    target = _session(user.id, "other-token", sid="abc")
    service, _ = _make_service([target])
    revoked, was_current = await service.revoke_session(user, "abc", "my-token")
    assert revoked is True
    assert was_current is False


@pytest.mark.asyncio
async def test_revoke_session_belongs_to_other_user_is_404_like() -> None:
    user = _user()
    target = _session("00000000-0000-0000-0000-000000000099", "x", sid="abc")
    service, db = _make_service([target])
    revoked, was_current = await service.revoke_session(user, "abc", "my-token")
    assert revoked is False
    assert was_current is False
    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_revoke_session_missing_id_returns_false() -> None:
    user = _user()
    service, db = _make_service([])  # scalar_one_or_none returns None
    revoked, _ = await service.revoke_session(user, "no-such-id", "tok")
    assert revoked is False
    db.delete.assert_not_called()


# ── revoke_other_sessions ────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_other_sessions_keeps_current() -> None:
    user = _user()
    current = _session(user.id, "tok", sid="me")
    other_a = _session(user.id, "tok-a", sid="a")
    other_b = _session(user.id, "tok-b", sid="b")
    service, db = _make_service([current, other_a, other_b])

    count = await service.revoke_other_sessions(user, "tok")
    assert count == 2
    deleted_args = [c.args[0] for c in db.delete.call_args_list]
    assert current not in deleted_args
    assert other_a in deleted_args
    assert other_b in deleted_args


@pytest.mark.asyncio
async def test_revoke_other_sessions_no_current_token_deletes_all() -> None:
    user = _user()
    s = _session(user.id, "x")
    service, db = _make_service([s])
    count = await service.revoke_other_sessions(user, current_raw_token=None)
    assert count == 1
    db.delete.assert_awaited()


# ── resend_verification_email ────────────────────────────────────


@pytest.mark.asyncio
async def test_resend_verification_already_verified_raises() -> None:
    user = _user(email_verified_at=datetime.now(tz=timezone.utc))
    service, _ = _make_service([])
    with pytest.raises(AuthError) as exc:
        await service.resend_verification_email(user)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_resend_verification_first_time_sends_email() -> None:
    user = _user()
    service, _ = _make_service([])
    # SETNX returns True on first call (key was free)
    service._redis.set = AsyncMock(return_value=True)
    service._redis.setex = AsyncMock()
    with pytest.MonkeyPatch.context() as m:
        sender = AsyncMock()
        m.setattr("psx_api.services.auth_service.send_verification_email", sender)
        await service.resend_verification_email(user)
    sender.assert_awaited_once()
    # Sender called with (email, token); token is fresh random string
    args, _kw = sender.call_args
    assert args[0] == user.email
    assert len(args[1]) > 20  # token_urlsafe(32) is ≥40 chars


@pytest.mark.asyncio
async def test_resend_verification_cooldown_blocks_second_call() -> None:
    user = _user()
    service, _ = _make_service([])
    # SETNX returns False on second call (key already set within the TTL)
    service._redis.set = AsyncMock(return_value=False)
    with pytest.raises(AuthError) as exc:
        await service.resend_verification_email(user)
    assert exc.value.status_code == 429
