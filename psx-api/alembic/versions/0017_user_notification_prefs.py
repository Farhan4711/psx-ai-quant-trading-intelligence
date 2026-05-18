"""Add notification_prefs JSONB to users

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-15

Phase 10 Step 95 — per-channel notification preferences.

Default value enables every kind so existing users see no behavioural
change. Schema is loose-JSONB (vs separate boolean columns) because
new notification kinds land regularly — `kmi_delisting`, `payment_events`,
`weekly_summary` etc — and we'd rather grow the JSON than the
migration count.

Read side (NotificationService.send): on every send, look up the
user's prefs; default to True if the key is missing so a new
notification kind isn't silently muted for existing users.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DEFAULT_PREFS = (
    '{'
    '"pump_dump": true, '
    '"kmi_delisting": true, '
    '"goal_milestone": true, '
    '"payment_events": true, '
    '"weekly_summary": true, '
    '"system": true'
    '}'
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notification_prefs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(f"'{_DEFAULT_PREFS}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "notification_prefs")
