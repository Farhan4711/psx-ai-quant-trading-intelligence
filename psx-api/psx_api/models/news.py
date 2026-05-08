from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")


class ArticleMention(Base):
    __tablename__ = "article_mentions"

    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="CASCADE"),
        primary_key=True,
    )
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


class CompanyAlias(Base):
    __tablename__ = "company_aliases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("symbol", "alias", name="uq_company_aliases_symbol_alias"),
    )


class ArticleSentiment(Base):
    __tablename__ = "article_sentiment"

    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    polarity: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
