"""Create model_predictions + macro_indicators

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-08

Tables:
  - model_predictions: every prediction we issue, plus the realised
    next-day direction once we have it. Step 46 retrain job reads this
    to compute rolling 30-day live accuracy and gate models.
  - macro_indicators: daily KIBOR/policy-rate/FX/oil/gold series for
    chart overlays + the prediction feature pipeline (Step 47).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── model_predictions ─────────────────────────────────────────
    op.create_table(
        "model_predictions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "symbol",
            sa.String(20),
            sa.ForeignKey("securities.symbol", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_version", sa.String(40), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("probability_up", sa.Numeric(6, 4), nullable=False),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("confidence_score", sa.Numeric(6, 4), nullable=False),
        # Realised at t+horizon, populated by the daily reconciliation job
        sa.Column("realised_direction", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "probability_up >= 0 AND probability_up <= 1",
            name="ck_model_predictions_prob_range",
        ),
        sa.CheckConstraint(
            "confidence IN ('high','medium','low')",
            name="ck_model_predictions_confidence",
        ),
    )
    op.create_index(
        "ix_model_predictions_symbol_date",
        "model_predictions",
        ["symbol", "as_of_date"],
    )
    # Used by the live-accuracy gauge per (symbol, model_version)
    op.create_index(
        "ix_model_predictions_version_date",
        "model_predictions",
        ["model_version", "as_of_date"],
    )

    # ── macro_indicators ──────────────────────────────────────────
    op.create_table(
        "macro_indicators",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("indicator", sa.String(40), nullable=False),
        sa.Column("value", sa.Numeric(20, 6), nullable=False),
        sa.Column("source", sa.String(40), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("date", "indicator"),
        sa.CheckConstraint(
            "indicator IN ('kibor_1m','kibor_3m','kibor_6m','kibor_12m',"
            "'sbp_policy_rate','pkr_usd','brent_usd','gold_pkr_per_tola')",
            name="ck_macro_indicator_whitelist",
        ),
    )
    op.create_index(
        "ix_macro_indicators_indicator_date",
        "macro_indicators",
        ["indicator", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_macro_indicators_indicator_date", table_name="macro_indicators")
    op.drop_table("macro_indicators")
    op.drop_index("ix_model_predictions_version_date", table_name="model_predictions")
    op.drop_index("ix_model_predictions_symbol_date", table_name="model_predictions")
    op.drop_table("model_predictions")
