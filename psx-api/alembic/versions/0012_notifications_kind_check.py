"""Add CHECK constraint on notifications.kind

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-08

The original 0011 migration documented the supported `kind` values in a
comment but didn't enforce the whitelist. Without it the table accepts
any string, and the UI / NotificationsBell silently fails to handle
unknown kinds. Add the constraint now while there's no production data
to migrate.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_VALID_KINDS = (
    "kmi_delisting",
    "pump_dump",
    "goal_milestone",
    "system",
)


def upgrade() -> None:
    # Sanitise any existing rows first — set unknown kinds to 'system'
    # so the new CHECK constraint doesn't fail at install time.
    # _VALID_KINDS is a hardcoded module-level tuple, not user input.
    op.execute(
        "UPDATE notifications SET kind = 'system' " "WHERE kind NOT IN ({})".format(  # noqa: S608
            ", ".join(f"'{k}'" for k in _VALID_KINDS)
        )
    )

    with op.batch_alter_table("notifications") as batch:
        batch.create_check_constraint(
            "ck_notifications_kind",
            "kind IN ({})".format(", ".join(f"'{k}'" for k in _VALID_KINDS)),
        )


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("ck_notifications_kind", type_="check")
