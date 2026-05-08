"""Phase 4 ORM models — peer aggregates, custom strategies, lessons, notifications, purification."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


# ── Step 60: peer aggregates ────────────────────────────────────────────


class PeerAggregate(Base):
    __tablename__ = "peer_aggregates"

    archetype: Mapped[str] = mapped_column(String(40), primary_key=True)
    age_bucket: Mapped[str] = mapped_column(String(20), primary_key=True)
    size_bucket: Mapped[str] = mapped_column(String(20), primary_key=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    median_ytd_return_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    top_holdings: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    sector_allocation: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    computed_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )


# ── Steps 62-63: user strategies ────────────────────────────────────────


class UserStrategy(Base):
    __tablename__ = "user_strategies"

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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules: Mapped[Any] = mapped_column(JSONB, nullable=False)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    forked_from: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("user_strategies.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_strategies_user_name"),
    )


# ── Step 64: notifications ──────────────────────────────────────────────


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )


# ── Step 65: purification records ───────────────────────────────────────


class PurificationRecord(Base):
    __tablename__ = "purification_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="CASCADE"),
        nullable=False,
    )
    dividends_received_pkr: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    purification_pct: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False, server_default="5"
    )
    purification_amount_pkr: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    marked_donated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "fiscal_year",
            "symbol",
            name="uq_purification_records_user_year_symbol",
        ),
    )


# ── Step 66: lessons + progress ─────────────────────────────────────────


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    quiz: Mapped[Any] = mapped_column(JSONB, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    quiz_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
