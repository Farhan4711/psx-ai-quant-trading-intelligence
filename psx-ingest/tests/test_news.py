"""
Unit tests for the news scraping pipeline.

No DB / no Redis / no network — we exercise:
- RSS parsing on fixture XML
- Body extraction on fixture HTML
- BaseNewsScraper throttle (verifies the rate-limit kicks in)
- Dedupe protocol (Redis mock returns "already seen")
- Lexicon sentiment + entity extraction round-trip
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from psx_ingest.news.base import (
    ArticleStub,
    BaseNewsScraper,
    NewsArticleRow,
    parse_rss_feed,
    parse_rss_pubdate,
)
from psx_ingest.news.extract import (
    aliases_from_securities,
    build_alias_index,
    extract_mentions,
)
from psx_ingest.news.sentiment import score_lexicon

# ── Fixtures ─────────────────────────────────────────────────────


SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Sample Business Feed</title>
  <item>
    <title>Engro Fertilizers posts record Q1 profit</title>
    <link>https://example.test/articles/engro-profit-q1</link>
    <pubDate>Sat, 10 May 2026 09:00:00 +0500</pubDate>
  </item>
  <item>
    <title>SBP holds policy rate at 12%</title>
    <link>https://example.test/articles/sbp-policy</link>
    <pubDate>Fri, 09 May 2026 17:30:00 +0500</pubDate>
  </item>
</channel></rss>
"""


SAMPLE_ARTICLE_HTML = """
<html><body>
  <article>
    <h1>Engro Fertilizers posts record Q1 profit</h1>
    <p>Engro Fertilizers Limited reported a strong Q1 with profit
       after tax up 18% year-on-year.</p>
    <p>The company beat consensus earnings estimates, helped by
       robust urea demand and improved gas allocation.</p>
    <script>tracker.send();</script>
  </article>
</body></html>
"""


# ── RSS / pubDate ────────────────────────────────────────────────


def test_parse_rss_feed_returns_stubs_in_order() -> None:
    stubs = parse_rss_feed(SAMPLE_RSS, source_slug="test")
    assert len(stubs) == 2
    assert stubs[0].url == "https://example.test/articles/engro-profit-q1"
    assert stubs[0].headline == "Engro Fertilizers posts record Q1 profit"
    assert stubs[0].published_at.tzinfo is not None
    # 09:00 PKT (UTC+5) -> 04:00 UTC
    assert stubs[0].published_at.hour == 4


def test_parse_rss_pubdate_handles_malformed() -> None:
    # Garbage falls back to now() rather than crashing the whole feed
    dt = parse_rss_pubdate("not a real date")
    assert dt.tzinfo is not None


def test_parse_rss_feed_empty_is_fine() -> None:
    stubs = parse_rss_feed("<rss><channel></channel></rss>", source_slug="test")
    assert stubs == []


# ── Body extraction ──────────────────────────────────────────────


def test_base_scraper_body_extracts_article_text() -> None:
    scraper = BaseNewsScraper()
    body = scraper.parse_article_body(SAMPLE_ARTICLE_HTML)
    # The <h1> headline is intentionally excluded — parse_article_body only
    # pulls <p> content; the headline comes from the RSS feed separately.
    assert "strong Q1 with profit" in body
    assert "tracker.send" not in body
    assert body.count("\n\n") >= 1  # paragraphs preserved


# ── Throttle ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_throttle_sleeps_between_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    # Mock the throttle setting so the test runs fast
    monkeypatch.setattr("psx_ingest.news.base.settings.scraper_min_delay_seconds", 1.0)
    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    scraper = BaseNewsScraper()
    await scraper._throttle()  # first call - no delay
    await scraper._throttle()  # second - should sleep
    assert any(s > 0 for s in sleeps), "Second throttle call should have slept"


# ── Dedupe ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dedupe_skips_already_seen_urls() -> None:
    redis_mock = AsyncMock()
    redis_mock.set.return_value = False  # SETNX says key already existed
    scraper = BaseNewsScraper(redis=redis_mock)
    assert (await scraper._should_fetch("https://example.test/x")) is False


@pytest.mark.asyncio
async def test_dedupe_allows_new_urls() -> None:
    redis_mock = AsyncMock()
    redis_mock.set.return_value = True
    scraper = BaseNewsScraper(redis=redis_mock)
    assert (await scraper._should_fetch("https://example.test/x")) is True


@pytest.mark.asyncio
async def test_dedupe_falls_open_on_redis_error() -> None:
    redis_mock = AsyncMock()
    redis_mock.set.side_effect = RuntimeError("redis down")
    scraper = BaseNewsScraper(redis=redis_mock)
    # Should NOT raise — falls through to letting the DB UNIQUE handle it.
    assert (await scraper._should_fetch("https://example.test/x")) is True


# ── End-to-end fetch_articles via mocked httpx ───────────────────


class _FixtureScraper(BaseNewsScraper):
    source_slug = "fixture"
    display_name = "Fixture"

    async def list_article_urls(self) -> list[ArticleStub]:
        return [
            ArticleStub(
                url="https://example.test/articles/engro-profit-q1",
                headline="Engro Fertilizers posts record Q1 profit",
                published_at=datetime.now(tz=UTC),
            )
        ]


@pytest.mark.asyncio
async def test_fetch_articles_pipeline() -> None:
    """End-to-end: list URLs → fetch HTML → parse body → yield."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_ARTICLE_HTML)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    redis_mock = AsyncMock()
    redis_mock.set.return_value = True

    scraper = _FixtureScraper(client=client, redis=redis_mock)
    out: list[NewsArticleRow] = []
    async with scraper:
        async for article in scraper.fetch_articles():
            out.append(article)
    await client.aclose()

    assert len(out) == 1
    article = out[0]
    assert article.source == "fixture"
    assert article.headline == "Engro Fertilizers posts record Q1 profit"
    assert "strong Q1 with profit" in article.body


# ── Sentiment + extraction ───────────────────────────────────────


def test_sentiment_positive_signal() -> None:
    result = score_lexicon(
        "Engro Fertilizers posts record Q1 profit. The company beat "
        "consensus earnings estimates, driven by strong urea demand."
    )
    assert result.polarity > 0
    assert result.event_type == "earnings"
    assert result.model_version.startswith("lexicon")


def test_sentiment_negative_signal() -> None:
    result = score_lexicon("Bank ABC reports a steep loss after regulatory fines.")
    assert result.polarity < 0
    # "fines" hits the regulatory pattern via "regulatory" word? No — let's
    # not over-assert event_type, just that polarity is negative.


def test_sentiment_negator_flips_meaning() -> None:
    pos = score_lexicon("Company reports record profit.")
    neg = score_lexicon("Company does not report record profit.")
    assert pos.polarity > 0
    assert neg.polarity <= 0


def test_entity_extraction_picks_up_company() -> None:
    aliases = build_alias_index(aliases_from_securities([("ENGRO", "Engro Corporation Limited")]))
    mentions = extract_mentions(
        "Engro Corporation posted strong results. ENGRO shares rose.",
        aliases,
    )
    # Two surface forms — "Engro Corporation" and "ENGRO" — both map to ENGRO.
    assert mentions.get("ENGRO", 0) >= 2


def test_entity_extraction_longer_alias_wins() -> None:
    """Longer aliases should be matched first so they don't get
    eaten by shorter substrings — e.g. 'Engro Fertilizers' must
    map to EFERT, not to ENGRO."""
    aliases = build_alias_index(
        [
            ("EFERT", "Engro Fertilizers"),
            ("ENGRO", "Engro"),
        ]
    )
    mentions = extract_mentions(
        "Engro Fertilizers reported record earnings.",
        aliases,
    )
    assert mentions.get("EFERT", 0) == 1
    assert mentions.get("ENGRO", 0) == 0


# ── Source-specific body extractors ──────────────────────────────


def test_dawn_body_extractor_uses_story_content_class() -> None:
    from psx_ingest.news.sources.dawn import DawnBusinessScraper

    html = """
    <html><body>
      <div class="story__content">
        <p>The KSE-100 index rose 240 points to close at 78,000.</p>
        <p>Banking and cement sectors led the rally.</p>
      </div>
    </body></html>
    """
    scraper = DawnBusinessScraper()
    body = scraper.parse_article_body(html)
    assert "KSE-100 index rose 240 points" in body
    assert "led the rally" in body


def test_tribune_body_extractor_uses_story_text_span() -> None:
    from psx_ingest.news.sources.tribune import TribuneBusinessScraper

    html = """
    <html><body>
      <span class="story-text">
        <p>The rupee gained 0.3% against the dollar.</p>
      </span>
    </body></html>
    """
    scraper = TribuneBusinessScraper()
    body = scraper.parse_article_body(html)
    assert "rupee gained 0.3%" in body
