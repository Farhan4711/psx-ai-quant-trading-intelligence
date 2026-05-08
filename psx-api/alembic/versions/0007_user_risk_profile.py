"""Add risk-profile fields to users

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "risk_archetype",
            sa.String(40),
            nullable=True,
            comment="One of: conservative_saver, cautious_beginner, balanced_builder, growth_seeker, aggressive_trader",
        ),
    )
    op.add_column(
        "users", sa.Column("risk_tolerance_score", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("time_horizon_score", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("knowledge_score", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "risk_profile_completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "risk_profile_completed_at")
    op.drop_column("users", "knowledge_score")
    op.drop_column("users", "time_horizon_score")
    op.drop_column("users", "risk_tolerance_score")
    op.drop_column("users", "risk_archetype")
