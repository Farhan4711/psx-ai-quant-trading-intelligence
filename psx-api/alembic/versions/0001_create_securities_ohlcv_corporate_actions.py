"""Create securities, ohlcv_daily, and corporate_actions tables

Revision ID: 0001
Revises:
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # TimescaleDB extension — idempotent, safe to re-run
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # ── securities ────────────────────────────────────────────────────────────
    op.create_table(
        "securities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=False),
        sa.Column("is_kmi_compliant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_kse100", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_kse30", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("market_cap_pkr", sa.BigInteger(), nullable=True),
        sa.Column("shares_outstanding", sa.BigInteger(), nullable=True),
        sa.Column("listed_at", sa.Date(), nullable=True),
        sa.Column("delisted_at", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_securities_symbol"),
    )
    op.create_index("ix_securities_symbol", "securities", ["symbol"])
    op.create_index("ix_securities_sector", "securities", ["sector"])
    op.create_index("ix_securities_is_active", "securities", ["is_active"])

    # ── ohlcv_daily (TimescaleDB hypertable) ──────────────────────────────────
    op.create_table(
        "ohlcv_daily",
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(12, 4), nullable=True),
        sa.Column("high", sa.Numeric(12, 4), nullable=True),
        sa.Column("low", sa.Numeric(12, 4), nullable=True),
        sa.Column("close", sa.Numeric(12, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("value_pkr", sa.Numeric(20, 2), nullable=True),
        sa.Column("adjusted_close", sa.Numeric(12, 4), nullable=True),
        sa.ForeignKeyConstraint(
            ["symbol"], ["securities.symbol"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )
    op.create_index("ix_ohlcv_daily_symbol_date_desc", "ohlcv_daily", ["symbol", sa.text("date DESC")])

    # Convert to TimescaleDB hypertable — partitioned by date, 1-month chunks
    op.execute(
        "SELECT create_hypertable('ohlcv_daily', 'date', "
        "chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);"
    )

    # ── corporate_actions ─────────────────────────────────────────────────────
    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("announcement_date", sa.Date(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("amount_per_share", sa.Numeric(12, 4), nullable=True),
        sa.Column("ratio_numerator", sa.Integer(), nullable=True),
        sa.Column("ratio_denominator", sa.Integer(), nullable=True),
        sa.Column("raw_announcement", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["symbol"], ["securities.symbol"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_corporate_actions_symbol", "corporate_actions", ["symbol"])
    op.create_index("ix_corporate_actions_action_type", "corporate_actions", ["action_type"])
    op.create_index("ix_corporate_actions_announcement_date", "corporate_actions", ["announcement_date"])


def downgrade() -> None:
    op.drop_table("corporate_actions")
    # Must drop hypertable the normal way — TimescaleDB handles the chunks
    op.drop_table("ohlcv_daily")
    op.drop_table("securities")
