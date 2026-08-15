from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnic_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    is_filer: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    shariah_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Risk profile (Phase 2 Step 34)
    risk_archetype: Mapped[str | None] = mapped_column(String(40), nullable=True)
    risk_tolerance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_horizon_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    knowledge_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_profile_completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Phase 4 (Step 59): opt-in to anonymous benchmarking + age bucketing
    share_anonymously: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    # TOTP second factor
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Step 95: per-kind notification mute toggles. Missing keys → True.
    notification_prefs: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default=(
            '{"pump_dump": true, "kmi_delisting": true, '
            '"goal_milestone": true, "payment_events": true, '
            '"weekly_summary": true, "system": true}'
        ),
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Store SHA-256 hash of the raw session token — raw token goes in HTTP-only cookie
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)

    __table_args__ = (Index("ix_user_sessions_user_id_expires", "user_id", "expires_at"),)

    def __repr__(self) -> str:
        return f"<UserSession {self.user_id} exp={self.expires_at}>"
