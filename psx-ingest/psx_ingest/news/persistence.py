"""
News persistence — turn `NewsArticleRow` objects into DB rows.

For each scraped article we:
  1. Upsert into `news_articles` keyed by URL.
  2. Extract company mentions (headline + first 800 chars of body —
     headlines are denser per character; full-body extraction can be
     a slow tail-end op when the article is multi-page).
  3. Insert one `article_mentions` row per mentioned symbol.
  4. Score sentiment (lexicon scorer; FinBERT later) and insert one
     `article_sentiment` row per mentioned symbol.

The whole flow is idempotent: re-scraping the same URL is a no-op
because:
  - `news_articles.url` is UNIQUE so the article INSERT … ON CONFLICT
    DO NOTHING bails out.
  - `article_mentions` / `article_sentiment` are composite-PK'd on
    article_id + symbol so the per-mention inserts also no-op.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from psx_ingest.news.base import NewsArticleRow
from psx_ingest.news.extract import (
    Alias,
    build_alias_index,
    extract_mentions,
)
from psx_ingest.news.sentiment import score_lexicon

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class IngestSummary:
    fetched: int = 0
    inserted: int = 0
    duplicates: int = 0
    errors: int = 0
    mentions_total: int = 0
    sentiment_rows: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "fetched": self.fetched,
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "errors": self.errors,
            "mentions_total": self.mentions_total,
            "sentiment_rows": self.sentiment_rows,
        }


async def load_alias_index(session: AsyncSession) -> list[Alias]:
    """Build the alias index from the securities + company_aliases tables.

    `company_aliases` adds curated overrides (e.g. "MCB" -> the bank,
    not "Mobile Country Code"); `securities.company_name` is the
    fallback. Both sources are joined and de-duped on (symbol, alias).
    """
    rows = (
        await session.execute(
            text(
                """
                SELECT symbol, company_name AS alias FROM securities
                WHERE is_active = TRUE
                UNION
                SELECT symbol, alias FROM company_aliases
                """
            )
        )
    ).all()
    # Also include the ticker itself as an alias.
    raw = [(r[0], r[1]) for r in rows if r[1]]
    raw.extend([(r[0], r[0]) for r in rows])
    return build_alias_index(raw)


async def upsert_article(session: AsyncSession, article: NewsArticleRow) -> str | None:
    """Insert the article. Returns the new article_id, or None if it
    already existed (URL UNIQUE conflict)."""
    result = await session.execute(
        text(
            """
            INSERT INTO news_articles
                (source, url, headline, body, published_at, language)
            VALUES
                (:source, :url, :headline, :body, :published_at, :language)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """
        ),
        {
            "source": article.source,
            "url": article.url,
            "headline": article.headline,
            "body": article.body,
            "published_at": article.published_at,
            "language": article.language,
        },
    )
    row = result.fetchone()
    return str(row[0]) if row else None


async def insert_mention(session: AsyncSession, article_id: str, symbol: str, count: int) -> None:
    await session.execute(
        text(
            """
            INSERT INTO article_mentions (article_id, symbol, match_count)
            VALUES (:article_id, :symbol, :count)
            ON CONFLICT (article_id, symbol) DO UPDATE
                SET match_count = EXCLUDED.match_count
            """
        ),
        {"article_id": article_id, "symbol": symbol, "count": count},
    )


async def insert_sentiment(
    session: AsyncSession,
    article_id: str,
    symbol: str,
    polarity: float,
    event_type: str,
    model_version: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO article_sentiment
                (article_id, symbol, polarity, event_type, model_version)
            VALUES
                (:article_id, :symbol, :polarity, :event_type, :model_version)
            ON CONFLICT (article_id, symbol) DO NOTHING
            """
        ),
        {
            "article_id": article_id,
            "symbol": symbol,
            "polarity": polarity,
            "event_type": event_type,
            "model_version": model_version,
        },
    )


async def ingest_article(
    session: AsyncSession,
    article: NewsArticleRow,
    aliases: list[Alias],
    summary: IngestSummary,
) -> None:
    """Insert article + per-symbol mention/sentiment rows. Catches errors
    per article so one bad row doesn't kill the whole batch."""
    summary.fetched += 1
    try:
        article_id = await upsert_article(session, article)
        if article_id is None:
            summary.duplicates += 1
            return
        summary.inserted += 1

        # Score the headline + first 800 chars together — captures the
        # lede where the verb-laden sentences live without paying for a
        # multi-page parse.
        snippet = (article.headline + "\n\n" + article.body)[:1000]
        mentions = extract_mentions(snippet, aliases)
        if not mentions:
            return

        # One mention row + one sentiment row per symbol.
        sentiment = score_lexicon(snippet)
        for symbol, count in mentions.items():
            await insert_mention(session, article_id, symbol, count)
            await insert_sentiment(
                session,
                article_id,
                symbol,
                polarity=sentiment.polarity,
                event_type=sentiment.event_type,
                model_version=sentiment.model_version,
            )
            summary.mentions_total += count
            summary.sentiment_rows += 1
    except Exception as exc:
        summary.errors += 1
        logger.error(
            "news.ingest_article_failed",
            url=article.url,
            error=str(exc),
        )
