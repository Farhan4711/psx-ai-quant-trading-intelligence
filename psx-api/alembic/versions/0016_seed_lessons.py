"""Seed the lessons table from psx_api.learning.curriculum

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-15

Phase 10 Step 93. Previously the lessons were seeded only after an
admin called `POST /api/v1/lessons/seed` (or whenever
`LessonService.seed_curriculum()` was invoked from a startup hook).
That made `/app/lessons` empty on a fresh deploy until someone
remembered to seed.

This migration imports `CURRICULUM` from the application package and
bulk_inserts the rows. It's idempotent the same way the service was —
we look up existing slugs first and only insert the missing ones.
That keeps the migration replay-safe if someone has already seeded
manually before upgrading.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Lazy import so this module is still parsable in CI environments
    # that don't have the application package on the path (alembic
    # invokes the file via importlib but the project pyproject.toml
    # already adds psx_api to sys.path before migrations run).
    from psx_api.learning.curriculum import CURRICULUM, quiz_to_jsonable

    # Use the live SQLAlchemy connection so we can read existing slugs
    # before inserting (idempotency).
    bind = op.get_bind()
    existing_slugs: set[str] = {
        r[0] for r in bind.execute(sa.text("SELECT slug FROM lessons")).fetchall()
    }

    payload = []
    for i, lesson in enumerate(CURRICULUM):
        if lesson.slug in existing_slugs:
            continue
        payload.append(
            {
                "slug": lesson.slug,
                "title": lesson.title,
                "category": lesson.category,
                "difficulty": lesson.difficulty,
                "body_md": lesson.body_md,
                # JSONB column — pass the Python list and alembic + the
                # postgresql JSONB type handle serialisation.
                "quiz": quiz_to_jsonable(lesson.quiz),
                "display_order": i,
            }
        )

    if not payload:
        return

    op.bulk_insert(
        sa.table(
            "lessons",
            sa.column("slug", sa.String),
            sa.column("title", sa.String),
            sa.column("category", sa.String),
            sa.column("difficulty", sa.Integer),
            sa.column("body_md", sa.Text),
            sa.column("quiz", postgresql.JSONB),
            sa.column("display_order", sa.Integer),
        ),
        payload,
    )


def downgrade() -> None:
    # We only delete the slugs we'd have inserted — leaves any
    # admin-edited rows intact.
    from psx_api.learning.curriculum import CURRICULUM

    slugs = [lesson.slug for lesson in CURRICULUM]
    if not slugs:
        return
    op.execute(
        sa.text("DELETE FROM lessons WHERE slug = ANY(:slugs)").bindparams(
            sa.bindparam("slugs", value=slugs, expanding=True)
        )
    )
