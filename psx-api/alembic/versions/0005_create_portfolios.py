"""Create portfolios, transactions, holdings_snapshot

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── portfolios ─────────────────────────────────────────────────
    op.create_table(
        "portfolios",
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
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    # Each user gets at most one default portfolio
    op.execute(
        "CREATE UNIQUE INDEX uq_portfolios_user_default ON portfolios (user_id) "
        "WHERE is_default = TRUE"
    )

    # ── transactions ──────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "symbol",
            sa.String(20),
            sa.ForeignKey("securities.symbol", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("price_per_share", sa.Numeric(12, 4), nullable=False),
        sa.Column("brokerage_pkr", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("fed_pkr", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("cvt_pkr", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("cgt_pkr", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "transaction_type IN ('buy','sell','dividend','bonus','rights')",
            name="ck_transactions_type",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_transactions_qty_positive"),
        sa.CheckConstraint("price_per_share >= 0", name="ck_transactions_price_nonneg"),
    )
    op.create_index("ix_transactions_portfolio_id", "transactions", ["portfolio_id"])
    op.create_index("ix_transactions_symbol", "transactions", ["symbol"])
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"])
    # Common dashboard query: per-portfolio chronological ledger
    op.create_index(
        "ix_transactions_portfolio_date",
        "transactions",
        ["portfolio_id", "transaction_date"],
    )

    # ── holdings_snapshot ─────────────────────────────────────────
    op.create_table(
        "holdings_snapshot",
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "symbol",
            sa.String(20),
            sa.ForeignKey("securities.symbol", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("avg_cost_pkr", sa.Numeric(12, 4), nullable=False),
        sa.Column("total_invested_pkr", sa.Numeric(20, 2), nullable=False),
        sa.Column(
            "realized_pnl_pkr", sa.Numeric(20, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_dividends_received_pkr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("portfolio_id", "symbol"),
    )


def downgrade() -> None:
    op.drop_table("holdings_snapshot")
    op.drop_index("ix_transactions_portfolio_date", table_name="transactions")
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_index("ix_transactions_symbol", table_name="transactions")
    op.drop_index("ix_transactions_portfolio_id", table_name="transactions")
    op.drop_table("transactions")
    op.execute("DROP INDEX IF EXISTS uq_portfolios_user_default")
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
