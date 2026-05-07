"""Add unique constraint to corporate_actions (symbol, action_type, announcement_date)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
