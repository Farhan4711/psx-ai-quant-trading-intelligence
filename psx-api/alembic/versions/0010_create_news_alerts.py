"""Create news_articles, article_mentions, article_sentiment, company_aliases, suspicious_days

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-08

Phase 3A + 3B foundation:
  - news_articles      raw scraped articles (Step 49)
  - article_mentions   which symbols each article mentions (Step 50)
  - company_aliases    symbol → list of name strings the matcher checks
  - article_sentiment  per-(article, symbol) sentiment polarity (Step 51)
  - suspicious_days    pump/dump alerts the rule + anomaly detectors emit
                       (Steps 54–56). One row per (symbol, date) where
                       a flag fired; severity is the highest-priority
                       trigger for that day.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── news_articles ─────────────────────────────────────────────
    op.create_table(
        "news_articles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "scraped_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="uq_news_articles_url"),
    )
    op.create_index("ix_news_articles_source_pub", "news_articles", ["source", "published_at"])
    op.create_index("ix_news_articles_pub", "news_articles", ["published_at"])

    # ── article_mentions ──────────────────────────────────────────
    op.create_table(
        "article_mentions",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("news_articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "symbol",
            sa.String(20),
            sa.ForeignKey("securities.symbol", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("article_id", "symbol"),
    )
    op.create_index("ix_article_mentions_symbol", "article_mentions", ["symbol"])

    # ── company_aliases ───────────────────────────────────────────
    op.create_table(
        "company_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "symbol",
            sa.String(20),
            sa.ForeignKey("securities.symbol", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "alias", name="uq_company_aliases_symbol_alias"),
    )
    op.create_index("ix_company_aliases_alias_lower", "company_aliases", [sa.text("lower(alias)")])

    # ── article_sentiment ─────────────────────────────────────────
    op.create_table(
        "article_sentiment",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("news_articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("polarity", sa.Numeric(4, 3), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=True),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column(
            "scored_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("article_id", "symbol"),
        sa.CheckConstraint(
            "polarity >= -1 AND polarity <= 1",
            name="ck_article_sentiment_polarity_range",
        ),
        sa.CheckConstraint(
            "event_type IS NULL OR event_type IN "
            "('earnings','guidance','regulatory','macro','mna','leadership','scandal','general')",
            name="ck_article_sentiment_event_type",
        ),
    )
    op.create_index("ix_article_sentiment_symbol", "article_sentiment", ["symbol"])

    # ── suspicious_days ───────────────────────────────────────────
    op.create_table(
        "suspicious_days",
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
        sa.Column("alert_date", sa.Date(), nullable=False),
        sa.Column("alert_type", sa.String(30), nullable=False),  # pump | dump
        sa.Column("severity", sa.String(10), nullable=False),  # low | medium | high
        sa.Column("vol_spike", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_change_pct", sa.Numeric(10, 2), nullable=False),
        sa.Column("anomaly_score", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "has_news_context", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "alert_date", name="uq_suspicious_days_symbol_date"),
        sa.CheckConstraint("alert_type IN ('pump','dump')", name="ck_suspicious_days_type"),
        sa.CheckConstraint(
            "severity IN ('low','medium','high')", name="ck_suspicious_days_severity"
        ),
    )
    op.create_index("ix_suspicious_days_date", "suspicious_days", ["alert_date"])
    op.create_index("ix_suspicious_days_symbol", "suspicious_days", ["symbol"])


def downgrade() -> None:
    for idx in (
        ("ix_suspicious_days_symbol", "suspicious_days"),
        ("ix_suspicious_days_date", "suspicious_days"),
        ("ix_article_sentiment_symbol", "article_sentiment"),
        ("ix_company_aliases_alias_lower", "company_aliases"),
        ("ix_article_mentions_symbol", "article_mentions"),
        ("ix_news_articles_pub", "news_articles"),
        ("ix_news_articles_source_pub", "news_articles"),
    ):
        op.drop_index(idx[0], table_name=idx[1])
    op.drop_table("suspicious_days")
    op.drop_table("article_sentiment")
    op.drop_table("company_aliases")
    op.drop_table("article_mentions")
    op.drop_table("news_articles")
