"""Cross-feature notifications (Phase 4 Step 64 + general inbox)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.community import Notification
from psx_api.models.users import User

# Mirrors the DB CHECK constraint added in migration 0012. Keeping this
# list as the single source of truth in the application means callers
# get a fast, descriptive error instead of an IntegrityError on flush.
VALID_KINDS = frozenset({"kmi_delisting", "pump_dump", "goal_milestone", "system"})


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def send(
        self,
        user_id: str,
        *,
        kind: str,
        title: str,
        body: str,
        link_path: str | None = None,
    ) -> Notification | None:
        """Insert a notification row honouring the user's per-kind
        preferences (Step 95). Returns None when the user has muted
        this kind — callers shouldn't treat that as an error."""
        if kind not in VALID_KINDS:
            raise ValueError(
                f"Unknown notification kind {kind!r}. " f"Must be one of: {sorted(VALID_KINDS)}"
            )
        # Per-kind mute: missing keys default to True (= unmuted) so a
        # new notification kind isn't silently muted for existing users.
        prefs = (
            await self._db.execute(select(User.notification_prefs).where(User.id == user_id))
        ).scalar_one_or_none() or {}
        if prefs.get(kind, True) is False:
            return None
        n = Notification(user_id=user_id, kind=kind, title=title, body=body, link_path=link_path)
        self._db.add(n)
        await self._db.flush()
        await self._db.refresh(n)
        return n

    async def list_for_user(self, user_id: str, *, limit: int = 50) -> list[Notification]:
        return list(
            (
                await self._db.execute(
                    select(Notification)
                    .where(Notification.user_id == user_id)
                    .order_by(desc(Notification.created_at))
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    async def unread_count(self, user_id: str) -> int:
        return int(
            (
                await self._db.execute(
                    select(func.count(Notification.id)).where(
                        Notification.user_id == user_id,
                        Notification.read_at.is_(None),
                    )
                )
            ).scalar_one()
        )

    async def mark_read(self, user_id: str, notification_id: str) -> None:
        await self._db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        await self._db.flush()

    async def mark_all_read(self, user_id: str) -> int:
        now = datetime.now(UTC)
        result = await self._db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=now)
        )
        await self._db.flush()
        return result.rowcount or 0
