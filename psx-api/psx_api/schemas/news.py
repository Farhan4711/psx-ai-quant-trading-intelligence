from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class NewsArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    url: str
    headline: str
    body: str
    published_at: datetime
    language: str


class ArticleWithSentiment(BaseModel):
    """Article + the polarity for the symbol the caller asked about."""

    id: str
    source: str
    url: str
    headline: str
    published_at: datetime
    polarity: Decimal | None = None
    event_type: str | None = None


class NewsPulseResponse(BaseModel):
    symbol: str
    as_of_date: date
    score: float  # in [-100, +100]
    article_count: int
    weighted_count: float
    top_articles: list[ArticleWithSentiment]
    explainer: str
