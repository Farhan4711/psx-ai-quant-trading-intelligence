"""
Auth service — signup, login, email verification, password reset, TOTP setup.

Session design:
  - On login, generate a 32-byte cryptographically random token.
  - Store SHA-256(token) in user_sessions.token_hash.
  - Set the raw token as an HTTP-only Secure SameSite=Lax cookie named `psx_session`.
  - On each authenticated request, read the cookie, hash it, look up the session.

Redis keys (TTL-bounded):
  email_verify:{token_hash}   → user_id  (TTL 24h)
  password_reset:{token_hash} → user_id  (TTL 1h)
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import pyotp  # type: ignore[import-not-found]
import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.config import settings
from psx_api.models.users import User, UserSession
from psx_api.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)

logger = structlog.get_logger(__name__)

_ph = PasswordHasher()

_SESSION_COOKIE = "psx_session"
_VERIFY_TTL = 86400       # 24 hours
_RESET_TTL = 3600         # 1 hour
_SESSION_TTL_DAYS = 30


def _sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthError(Exception):
    """Raised for expected auth failures (wrong password, expired token, etc.)."""
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:  # type: ignore[type-arg]
        self._db = db
        self._redis = redis

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------

    async def signup(self, email: str, password: str, full_name: str | None) -> User:
        existing = await self._db.execute(select(User).where(User.email == email.lower()))
        if existing.scalar_one_or_none():
            raise AuthError("An account with this email already exists.", status_code=409)

        user = User(
            email=email.lower(),
            password_hash=_ph.hash(password),
            full_name=full_name,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)

        # Send verification email
        token = secrets.token_urlsafe(32)
        token_hash = _sha256(token)
        await self._redis.setex(f"email_verify:{token_hash}", _VERIFY_TTL, user.id)
        await send_verification_email(email, token)

        logger.info("User signed up", user_id=user.id, email=user.email)
        return user

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    async def verify_email(self, token: str) -> User:
        token_hash = _sha256(token)
        user_id = await self._redis.get(f"email_verify:{token_hash}")
        if not user_id:
            raise AuthError("Invalid or expired verification link.", status_code=400)

        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthError("User not found.", status_code=404)

        user.email_verified_at = datetime.now(tz=timezone.utc)
        await self._db.flush()
        await self._redis.delete(f"email_verify:{token_hash}")
        logger.info("Email verified", user_id=user.id)
        return user

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(
        self,
        email: str,
        password: str,
        totp_code: str | None,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[User, str]:
        """
        Returns (user, raw_session_token) on success.
        Raises AuthError on failure.
        """
        result = await self._db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise AuthError("Invalid email or password.", status_code=401)

        try:
            _ph.verify(user.password_hash, password)
        except VerifyMismatchError:
            raise AuthError("Invalid email or password.", status_code=401)

        # Rehash if argon2 parameters have been upgraded
        if _ph.check_needs_rehash(user.password_hash):
            user.password_hash = _ph.hash(password)

        # TOTP check
        if user.totp_enabled:
            if not totp_code:
                raise AuthError("TOTP code required.", status_code=401)
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(totp_code, valid_window=1):
                raise AuthError("Invalid TOTP code.", status_code=401)

        # Create session
        raw_token = secrets.token_urlsafe(32)
        session = UserSession(
            user_id=user.id,
            token_hash=_sha256(raw_token),
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=_SESSION_TTL_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self._db.add(session)
        await self._db.flush()

        logger.info("User logged in", user_id=user.id)
        return user, raw_token

    # ------------------------------------------------------------------
    # Session lookup (used per-request by auth dependency)
    # ------------------------------------------------------------------

    async def get_session_user(self, raw_token: str) -> User | None:
        token_hash = _sha256(raw_token)
        now = datetime.now(tz=timezone.utc)
        result = await self._db.execute(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.expires_at > now,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return None

        user_result = await self._db.execute(select(User).where(User.id == session.user_id))
        return user_result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(self, raw_token: str) -> None:
        token_hash = _sha256(raw_token)
        result = await self._db.execute(
            select(UserSession).where(UserSession.token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        if session:
            await self._db.delete(session)
            await self._db.flush()

    # ------------------------------------------------------------------
    # Session management (settings → security tab)
    # ------------------------------------------------------------------

    async def list_sessions(
        self, user: User, current_raw_token: str | None
    ) -> list[dict[str, Any]]:
        """All non-expired sessions for this user, newest first. The
        session matching `current_raw_token` is flagged `is_current` so
        the UI can render "this device" indicator + prevent the user
        from accidentally revoking it."""
        now = datetime.now(tz=timezone.utc)
        result = await self._db.execute(
            select(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.expires_at > now,
            )
            .order_by(UserSession.created_at.desc())
        )
        rows = result.scalars().all()
        current_hash = _sha256(current_raw_token) if current_raw_token else None
        return [
            {
                "id": s.id,
                "user_agent": s.user_agent,
                "ip_address": str(s.ip_address) if s.ip_address else None,
                "created_at": s.created_at,
                "expires_at": s.expires_at,
                "is_current": s.token_hash == current_hash,
            }
            for s in rows
        ]

    async def revoke_session(
        self, user: User, session_id: str, current_raw_token: str | None
    ) -> tuple[bool, bool]:
        """Delete a single session. Returns `(revoked, was_current)` where
        `revoked=False` means the session didn't exist (or belonged to
        another user, deliberately conflated to avoid leaking existence).
        `was_current=True` tells the router to also clear the cookie."""
        result = await self._db.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session or session.user_id != user.id:
            return False, False
        current_hash = _sha256(current_raw_token) if current_raw_token else None
        was_current = session.token_hash == current_hash
        await self._db.delete(session)
        await self._db.flush()
        return True, was_current

    async def revoke_other_sessions(
        self, user: User, current_raw_token: str | None
    ) -> int:
        """Delete every session for this user EXCEPT the one matching
        the caller's cookie. Returns the count of deleted sessions.
        Used by the "Sign out everywhere else" button."""
        current_hash = _sha256(current_raw_token) if current_raw_token else None
        result = await self._db.execute(
            select(UserSession).where(UserSession.user_id == user.id)
        )
        rows = result.scalars().all()
        deleted = 0
        for s in rows:
            if s.token_hash == current_hash:
                continue
            await self._db.delete(s)
            deleted += 1
        if deleted:
            await self._db.flush()
        return deleted

    # ------------------------------------------------------------------
    # Resend verification email
    # ------------------------------------------------------------------

    async def resend_verification_email(self, user: User) -> None:
        """Issue a fresh verification token and re-email it. Rate-limit
        via Redis: one send per 5 minutes per user-id, so a malicious
        actor can't use a known email + leaked cookie to spam the
        inbox.

        Raises AuthError with status_code=429 when rate-limited so the
        router can surface a clean "wait a bit" response."""
        if user.email_verified_at is not None:
            raise AuthError("This email is already verified.", status_code=400)

        cooldown_key = f"email_verify_cooldown:{user.id}"
        # SETNX with 5-minute TTL — succeeds the first time, fails
        # while the key is still set.
        acquired = await self._redis.set(
            cooldown_key, "1", ex=300, nx=True
        )
        if not acquired:
            raise AuthError(
                "We just sent a verification email. Wait 5 minutes before requesting another.",
                status_code=429,
            )

        token = secrets.token_urlsafe(32)
        token_hash = _sha256(token)
        await self._redis.setex(f"email_verify:{token_hash}", _VERIFY_TTL, user.id)
        await send_verification_email(user.email, token)
        logger.info("Verification email resent", user_id=user.id)

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    async def forgot_password(self, email: str) -> None:
        result = await self._db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            # Don't reveal whether the email exists
            return

        token = secrets.token_urlsafe(32)
        token_hash = _sha256(token)
        await self._redis.setex(f"password_reset:{token_hash}", _RESET_TTL, user.id)
        await send_password_reset_email(email, token)

    async def reset_password(self, token: str, new_password: str) -> None:
        token_hash = _sha256(token)
        user_id = await self._redis.get(f"password_reset:{token_hash}")
        if not user_id:
            raise AuthError("Invalid or expired reset link.", status_code=400)

        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthError("User not found.", status_code=404)

        user.password_hash = _ph.hash(new_password)
        await self._db.flush()
        await self._redis.delete(f"password_reset:{token_hash}")
        # Invalidate all existing sessions for this user
        await self._db.execute(
            UserSession.__table__.delete().where(UserSession.user_id == user.id)
        )
        logger.info("Password reset", user_id=user.id)

    # ------------------------------------------------------------------
    # TOTP setup
    # ------------------------------------------------------------------

    async def totp_setup(self, user: User) -> dict[str, str]:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="PSX AI Trading")
        # Store secret provisionally — only persist once confirmed via totp_confirm
        await self._redis.setex(f"totp_pending:{user.id}", 600, secret)
        return {"secret": secret, "provisioning_uri": uri}

    async def totp_confirm(self, user: User, totp_code: str) -> None:
        secret_raw = await self._redis.get(f"totp_pending:{user.id}")
        if not secret_raw:
            raise AuthError("TOTP setup session expired — start over.", status_code=400)
        secret = secret_raw if isinstance(secret_raw, str) else secret_raw.decode()
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code, valid_window=1):
            raise AuthError("Invalid TOTP code.", status_code=400)

        user.totp_secret = secret
        user.totp_enabled = True
        await self._db.flush()
        await self._redis.delete(f"totp_pending:{user.id}")
        logger.info("TOTP enabled", user_id=user.id)

    async def totp_disable(self, user: User, totp_code: str) -> None:
        if not user.totp_enabled or not user.totp_secret:
            raise AuthError("TOTP is not enabled.", status_code=400)
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise AuthError("Invalid TOTP code.", status_code=400)
        user.totp_secret = None
        user.totp_enabled = False
        await self._db.flush()
        logger.info("TOTP disabled", user_id=user.id)
