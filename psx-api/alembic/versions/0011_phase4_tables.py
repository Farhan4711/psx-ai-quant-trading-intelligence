"""Phase 4: opt-in sharing, peer aggregates, custom strategies, lessons, notifications, purification

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Step 59: opt-in sharing flag + age (for bucketing) ────────
    op.add_column(
        "users",
        sa.Column("share_anonymously", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))

    # ── Step 60: peer_aggregates (computed nightly) ───────────────
    # One row per (archetype, age_bucket, size_bucket). Stores median
    # YTD return, top-10 holdings, sector mix, sample count.
    op.create_table(
        "peer_aggregates",
        sa.Column("archetype", sa.String(40), nullable=False),
        sa.Column("age_bucket", sa.String(20), nullable=False),
        sa.Column("size_bucket", sa.String(20), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("median_ytd_return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("top_holdings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sector_allocation", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("archetype", "age_bucket", "size_bucket"),
        sa.CheckConstraint(
            "sample_count >= 0", name="ck_peer_aggregates_sample_count"
        ),
    )

    # ── Steps 62-63: user-defined strategies + marketplace ────────
    op.create_table(
        "user_strategies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # JSON rule chain: { entry: [...], exit: [...], position: {...} }
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "forked_from",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("user_strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_user_strategies_user_name"),
    )
    op.create_index("ix_user_strategies_user_id", "user_strategies", ["user_id"])
    # Marketplace browse index — only public ones
    op.execute(
        "CREATE INDEX ix_user_strategies_public ON user_strategies (created_at DESC) "
        "WHERE is_public = TRUE"
    )

    # ── Step 64: notifications (cross-feature inbox) ──────────────
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 'kmi_delisting' | 'pump_dump' | 'goal_milestone' | 'system'
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        # Optional: route the user can click to act on it
        sa.Column("link_path", sa.String(500), nullable=True),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "read_at", "created_at"],
    )

    # ── Step 65: purification_records ─────────────────────────────
    # One row per (user, fiscal_year, symbol) — records purification
    # owed for cash dividends from KMI-compliant holdings.
    op.create_table(
        "purification_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column(
            "symbol",
            sa.String(20),
            sa.ForeignKey("securities.symbol", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dividends_received_pkr", sa.Numeric(20, 2), nullable=False),
        sa.Column("purification_pct", sa.Numeric(6, 4), nullable=False, server_default="5"),
        sa.Column("purification_amount_pkr", sa.Numeric(20, 2), nullable=False),
        sa.Column("marked_donated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "fiscal_year", "symbol",
            name="uq_purification_records_user_year_symbol",
        ),
    )

    # ── Step 66: lessons + user_lesson_progress ───────────────────
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("body_md", sa.Text(), nullable=False),
        # JSON quiz: list of {question, options[], correct_index}
        sa.Column("quiz", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_lessons_slug"),
    )

    op.create_table(
        "user_lesson_progress",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("quiz_score", sa.SmallInteger(), nullable=True),  # 0..100
        sa.Column(
            "last_seen_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "lesson_id"),
        sa.CheckConstraint(
            "quiz_score IS NULL OR (quiz_score >= 0 AND quiz_score <= 100)",
            name="ck_user_lesson_progress_score_range",
        ),
    )


def downgrade() -> None:
    op.drop_table("user_lesson_progress")
    op.drop_table("lessons")
    op.drop_table("purification_records")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_table("notifications")
    op.execute("DROP INDEX IF EXISTS ix_user_strategies_public")
    op.drop_index("ix_user_strategies_user_id", table_name="user_strategies")
    op.drop_table("user_strategies")
    op.drop_table("peer_aggregates")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "share_anonymously")
