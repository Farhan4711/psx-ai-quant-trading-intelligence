"""Subscription plans + user subscriptions

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-08

Phase 5 Step 72: three-tier pricing (Free, Pro, Pro+). Plan rows are
seeded by this migration so the pricing page works on a fresh deploy.

A `user_subscriptions` row records the user's active plan + the
external billing-provider reference (Stripe customer/subscription IDs
or local-Pakistani-gateway equivalents). Local PKR processing via
Stripe Atlas isn't viable for retail Pakistanis today, so the
`provider` column is left flexible: we'll integrate JazzCash /
Easypaisa / a SafePay alternative when revenue justifies it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── subscription_plans ────────────────────────────────────────
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(40), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("tagline", sa.String(200), nullable=False),
        sa.Column("price_pkr_monthly", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_pkr_annual", sa.Numeric(10, 2), nullable=True),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_subscription_plans_slug"),
    )

    # ── user_subscriptions ────────────────────────────────────────
    op.create_table(
        "user_subscriptions",
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
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        # External billing reference (Stripe customer ID, JazzCash txn, etc.)
        sa.Column("provider", sa.String(40), nullable=True),
        sa.Column("provider_subscription_id", sa.String(200), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
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
            "status IN ('active', 'past_due', 'canceled', 'trialing', 'incomplete')",
            name="ck_user_subscriptions_status",
        ),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])
    # Only one active subscription per user at any time
    op.execute(
        "CREATE UNIQUE INDEX uq_user_subscriptions_user_active "
        "ON user_subscriptions (user_id) "
        "WHERE status IN ('active', 'trialing')"
    )

    # ── seed plans ────────────────────────────────────────────────
    plans = [
        {
            "slug": "free",
            "name": "Free",
            "tagline": "Everything 90% of investors actually need.",
            "price_pkr_monthly": "0",
            "price_pkr_annual": "0",
            "features": [
                "Browse all PSX stocks with charts and announcements",
                "Watchlist with live quotes",
                "1 portfolio with full tax-aware tracking",
                "8 technical indicators with plain-English interpretation",
                "Sector comparison + heatmap",
                "Shariah Mode + dividend purification",
                "Risk profile + goals planner",
                "Filer vs non-filer tax simulator",
            ],
            "display_order": 1,
        },
        {
            "slug": "pro",
            "name": "Pro",
            "tagline": "For the engaged investor who wants the analyst layer.",
            "price_pkr_monthly": "900",
            "price_pkr_annual": "9000",  # ~PKR 750/mo annual
            "features": [
                "Everything in Free",
                "Predictions on all stocks (Free sees top 20 only)",
                "News sentiment + News Pulse on every stock",
                "Pump-and-dump anomaly alerts",
                "Unlimited portfolios",
                "Custom no-code strategy builder",
                "Full backtest engine with trade narration",
                "Macro overlays on every price chart",
            ],
            "display_order": 2,
        },
        {
            "slug": "pro_plus",
            "name": "Pro+",
            "tagline": "Power users and small institutional desks.",
            "price_pkr_monthly": "2500",
            "price_pkr_annual": "25000",
            "features": [
                "Everything in Pro",
                "API access (rate-limited)",
                "Advanced portfolio rebalancing recommendations",
                "Priority support, < 24h response",
                "Early access to new features",
                "Anonymized peer benchmarking with peer holdings reveal",
                "Strategy marketplace publishing privileges",
            ],
            "display_order": 3,
        },
    ]

    op.bulk_insert(
        sa.table(
            "subscription_plans",
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
            sa.column("tagline", sa.String),
            sa.column("price_pkr_monthly", sa.Numeric),
            sa.column("price_pkr_annual", sa.Numeric),
            sa.column("features", postgresql.JSONB),
            sa.column("display_order", sa.Integer),
        ),
        plans,
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_user_subscriptions_user_active")
    op.drop_index("ix_user_subscriptions_user_id", table_name="user_subscriptions")
    op.drop_table("user_subscriptions")
    op.drop_table("subscription_plans")
