"""News + sentiment read service."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.news import ArticleMention, ArticleSentiment, NewsArticle
from psx_api.news.pulse import PulseInput, compute_pulse


class NewsService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def articles_for_symbol(
        self, symbol: str, *, limit: int = 20
    ) -> list[dict]:
        rows = (
            await self._db.execute(
                select(
                    NewsArticle.id,
                    NewsArticle.source,
                    NewsArticle.url,
                    NewsArticle.headline,
                    NewsArticle.published_at,
                    ArticleSentiment.polarity,
                    ArticleSentiment.event_type,
                )
                .join(ArticleMention, ArticleMention.article_id == NewsArticle.id)
                .outerjoin(
                    ArticleSentiment,
                    (ArticleSentiment.article_id == NewsArticle.id)
                    & (ArticleSentiment.symbol == ArticleMention.symbol),
                )
                .where(ArticleMention.symbol == symbol.upper())
                .order_by(desc(NewsArticle.published_at))
                .limit(limit)
            )
        ).all()
        return [
            {
                "id": r[0],
                "source": r[1],
                "url": r[2],
                "headline": r[3],
                "published_at": r[4],
                "polarity": r[5],
                "event_type": r[6],
            }
            for r in rows
        ]

    async def pulse(self, symbol: str, *, today: date | None = None) -> dict:
        today = today or datetime.now(timezone.utc).date()
        cutoff_dt = datetime.combine(
            today - timedelta(days=14), datetime.min.time(), tzinfo=timezone.utc
        )

        rows = (
            await self._db.execute(
                select(
                    NewsArticle.id,
                    NewsArticle.source,
                    NewsArticle.url,
                    NewsArticle.headline,
                    NewsArticle.published_at,
                    ArticleSentiment.polarity,
                    ArticleSentiment.event_type,
                )
                .join(
                    ArticleSentiment, ArticleSentiment.article_id == NewsArticle.id
                )
                .where(
                    ArticleSentiment.symbol == symbol.upper(),
                    NewsArticle.published_at >= cutoff_dt,
                )
                .order_by(desc(NewsArticle.published_at))
            )
        ).all()

        # Compute pulse from polarity rows
        pulse_inputs = [
            PulseInput(
                polarity=float(r[5]) if r[5] is not None else 0.0,
                published_on=r[4].date(),
            )
            for r in rows
            if r[5] is not None
        ]
        score = compute_pulse(pulse_inputs, today=today)

        # Top 3 by absolute polarity * recency for the UI display
        scored_articles = [
            {
                "row": r,
                "weight": (
                    abs(float(r[5])) if r[5] is not None else 0.0
                ),
                "recency_days": max(0, (today - r[4].date()).days),
            }
            for r in rows
        ]
        scored_articles.sort(
            key=lambda a: a["weight"] - a["recency_days"] * 0.05, reverse=True
        )
        top = scored_articles[:3]
        top_articles = [
            {
                "id": a["row"][0],
                "source": a["row"][1],
                "url": a["row"][2],
                "headline": a["row"][3],
                "published_at": a["row"][4],
                "polarity": a["row"][5],
                "event_type": a["row"][6],
            }
            for a in top
        ]

        return {
            "symbol": symbol.upper(),
            "as_of_date": today,
            "score": score.score,
            "article_count": score.article_count,
            "weighted_count": score.weighted_count,
            "top_articles": top_articles,
            "explainer": _explainer(score.score, score.article_count),
        }


def _explainer(score: float, count: int) -> str:
    if count == 0:
        return "No tagged news in the last 14 days."
    if score >= 50:
        return f"Strong positive coverage: {count} headlines, sentiment +{score:.0f} / 100."
    if score >= 15:
        return f"Mildly positive coverage: {count} headlines, sentiment +{score:.0f} / 100."
    if score <= -50:
        return f"Strong negative coverage: {count} headlines, sentiment {score:.0f} / 100."
    if score <= -15:
        return f"Mildly negative coverage: {count} headlines, sentiment {score:.0f} / 100."
    return f"Mixed / neutral: {count} headlines, net sentiment {score:.0f} / 100."
