"""Add unique constraint to corporate_actions (symbol, action_type, announcement_date)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_corporate_actions_symbol_type_date",
        "corporate_actions",
        ["symbol", "action_type", "announcement_date"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_corporate_actions_symbol_type_date",
        "corporate_actions",
        type_="unique",
    )
