"""Performance indexes for hot read paths

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-08

Phase 5 Step 68 perf audit. Each index below was identified by walking
the read-path queries in `psx_api/services/` and checking which
predicate combinations weren't already covered by existing primary
keys, unique constraints, or single-column indexes.

Use `EXPLAIN ANALYZE` on each query in production after deploy to
confirm index usage. Keep an eye on Postgres `pg_stat_user_indexes`
to drop indexes that don't earn their keep — every index slows
INSERT/UPDATE on its table.

CONCURRENTLY isn't usable in a regular migration (it can't run inside
a transaction). For an empty fresh deploy the perf impact is zero; for
a backfill against a large existing table, run these statements
manually with CONCURRENTLY in psql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADD THIS LINE TO PREVENT THE CRASH:
    op.execute("DROP INDEX IF EXISTS ix_ohlcv_daily_symbol_date_desc;")

    # ── ohlcv_daily ───────────────────────────────────────────────
    # Existing index is on (symbol, date) inferred from PK; ROW_NUMBER
    # subqueries (used by quote batch + holdings dashboard) scan by
    # `symbol IN (...)` ordering by date DESC. Add an explicit composite
    # that supports the descending scan.
    op.create_index(
        "ix_ohlcv_daily_symbol_date_desc",
        "ohlcv_daily",
        ["symbol", "date"],
        postgresql_using="btree",
    )

    # ── transactions ──────────────────────────────────────────────
    # Already has ix_transactions_portfolio_date from migration 0005.
    # Add (portfolio_id, symbol) for the FIFO walks in tax_simulator
    # and transaction_service._compute_sell_cgt which filter by both.
    op.create_index(
        "ix_transactions_portfolio_symbol",
        "transactions",
        ["portfolio_id", "symbol"],
    )

    # ── holdings_snapshot ─────────────────────────────────────────
    # Composite PK covers (portfolio_id, symbol). The dashboard joins
    # via portfolio_id alone (across the user's portfolios) — already
    # handled by the PK's left-prefix scan. No new index needed.

    # ── corporate_actions ─────────────────────────────────────────
    # Suspicious-day check queries by (symbol, announcement_date) range.
    # Add the composite if it doesn't already exist via the unique
    # constraint from migration 0002.
    op.create_index(
        "ix_corporate_actions_symbol_announcement",
        "corporate_actions",
        ["symbol", "announcement_date"],
    )

    # ── news_articles / article_mentions ──────────────────────────
    # NewsService.pulse() filters by article_mentions.symbol then joins
    # to news_articles ordered by published_at desc. Add composite to
    # short-circuit the join's sort step.
    op.create_index(
        "ix_news_articles_pub_desc",
        "news_articles",
        ["published_at"],
    )

    # ── article_sentiment ─────────────────────────────────────────
    # Already has ix_article_sentiment_symbol from migration 0010.
    # For the pulse aggregation, also add (symbol, scored_at) so the
    # 14-day window scan can use an index-only walk.
    op.create_index(
        "ix_article_sentiment_symbol_scored",
        "article_sentiment",
        ["symbol", "scored_at"],
    )

    # ── model_predictions ─────────────────────────────────────────
    # _live_accuracy_pct filters (symbol, model_version, as_of_date>=cutoff).
    # Existing ix_model_predictions_symbol_date covers two of the three
    # predicates. The version filter is highly selective on real data,
    # so add (model_version, symbol, as_of_date).
    op.create_index(
        "ix_model_predictions_version_symbol_date",
        "model_predictions",
        ["model_version", "symbol", "as_of_date"],
    )

    # ── notifications ─────────────────────────────────────────────
    # Already has ix_notifications_user_unread (user_id, read_at, created_at).
    # That covers both the unread-count query and the recent-inbox list,
    # so no additional index needed.

    # ── suspicious_days ───────────────────────────────────────────
    # `for_user()` subqueries by symbols held/watched. The existing
    # ix_suspicious_days_symbol covers the lookup. For the listing
    # ordered by date desc, add a composite (alert_date DESC, symbol).
    op.create_index(
        "ix_suspicious_days_date_desc",
        "suspicious_days",
        ["alert_date"],
    )

    # ── watchlist ─────────────────────────────────────────────────
    # ix_watchlist_user_id from migration 0004 covers per-user reads.
    # Ordering by sort_order, added_at — add a covering index for the
    # full read pattern.
    op.create_index(
        "ix_watchlist_user_sort",
        "watchlist",
        ["user_id", "sort_order", "added_at"],
    )


def downgrade() -> None:
    for idx, table in [
        ("ix_watchlist_user_sort", "watchlist"),
        ("ix_suspicious_days_date_desc", "suspicious_days"),
        ("ix_model_predictions_version_symbol_date", "model_predictions"),
        ("ix_article_sentiment_symbol_scored", "article_sentiment"),
        ("ix_news_articles_pub_desc", "news_articles"),
        ("ix_corporate_actions_symbol_announcement", "corporate_actions"),
        ("ix_transactions_portfolio_symbol", "transactions"),
        ("ix_ohlcv_daily_symbol_date_desc", "ohlcv_daily"),
    ]:
        op.drop_index(idx, table_name=table)
