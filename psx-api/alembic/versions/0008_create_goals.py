"""Create goals table

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
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
        sa.Column("goal_type", sa.String(30), nullable=False),
        sa.Column("target_amount_pkr", sa.Numeric(20, 2), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column(
            "current_amount_pkr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "monthly_contribution_pkr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "linked_portfolio_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("portfolios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "goal_type IN "
            "('retirement','hajj','education','home','marriage','emergency_fund','custom')",
            name="ck_goals_type",
        ),
        sa.CheckConstraint("target_amount_pkr > 0", name="ck_goals_target_positive"),
        sa.CheckConstraint("current_amount_pkr >= 0", name="ck_goals_current_nonneg"),
        sa.CheckConstraint("monthly_contribution_pkr >= 0", name="ck_goals_contribution_nonneg"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_table("goals")
