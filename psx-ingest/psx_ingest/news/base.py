"""
Base news scraper — shared HTTP + dedupe + body-extraction primitives.

Every concrete source (Dawn, Brecorder, Profit, The News, Tribune)
subclasses `BaseNewsScraper` and only has to implement two things:
    1. `list_article_urls()` — return `(url, published_at, headline)` tuples
       for recent articles, typically by parsing the source's RSS feed
       or HTML index page.
    2. `parse_article_body(html)` — return the article's plain-text body
       given the raw HTML of the article page.

Everything else — HTTP rate limiting, redis URL dedupe, retries,
User-Agent identification, robots-respecting timing — is here.

Polite-scraper policy
---------------------
- Minimum **3 seconds** between requests to the same domain
  (matches the existing DPS / PUCARS scrapers — see config.scraper_min_delay_seconds).
- User-Agent identifies us as educational/non-commercial with a
  pointer to LICENSING_NOTICE.md so site owners can contact us.
- We skip URLs we've already ingested via a Redis SETNX dedupe key
  with 60-day TTL — long enough that we don't re-fetch a stale article,
  short enough that a hard-reset of the news_articles table still
  re-ingests them.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx
import structlog
from bs4 import BeautifulSoup

from psx_ingest.config import settings

logger = structlog.get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "PSX-AI-TradingSystem/0.1 (educational; non-commercial; "
        "contact: see LICENSING_NOTICE.md)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-PK,en;q=0.9",
}

# Articles older than this on first sight are skipped — they're unlikely
# to move prices and they bloat the table. Tune up later if we want
# backfill.
_MAX_ARTICLE_AGE_DAYS = 14

# How long Redis remembers a seen URL. 60 days = comfortably longer
# than _MAX_ARTICLE_AGE_DAYS so we never re-fetch a still-relevant
# article, but short enough that a DB wipe-and-rerun works.
_DEDUPE_TTL_SECONDS = 60 * 24 * 60 * 60


@dataclass(frozen=True)
class NewsArticleRow:
    """Normalised article — what every scraper hands back to persistence."""

    source: str
    url: str
    headline: str
    body: str
    published_at: datetime  # always UTC-aware
    language: str = "en"


@dataclass(frozen=True)
class ArticleStub:
    """One row from a listing/RSS feed — body not yet fetched."""

    url: str
    headline: str
    published_at: datetime  # always UTC-aware


class BaseNewsScraper:
    """Subclass + implement `list_article_urls` and `parse_article_body`."""

    #: Slug stored in `news_articles.source`. Subclasses override.
    source_slug: str = "base"
    #: Human label used in logs.
    display_name: str = "Base"

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        redis: object | None = None,
    ) -> None:
        # Tests inject a mock client; production builds one per `async with`.
        self._client_external = client is not None
        self._client = client
        # Optional redis dedupe — when missing (e.g. unit tests) we just skip
        # dedupe; the news_articles.url UNIQUE constraint is the second line
        # of defence so we still won't duplicate-insert.
        self._redis = redis
        self._last_request_at: float = 0.0

    # ── Lifecycle ────────────────────────────────────────────────

    async def __aenter__(self) -> "BaseNewsScraper":
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=_DEFAULT_HEADERS,
                timeout=httpx.Timeout(20.0),
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if not self._client_external and self._client is not None:
            await self._client.aclose()

    # ── HTTP helpers ─────────────────────────────────────────────

    async def _get(self, url: str) -> httpx.Response | None:
        """Throttled GET. Returns None on 4xx/5xx so the caller can skip
        and continue rather than aborting the whole scrape."""
        await self._throttle()
        assert self._client is not None
        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            logger.warning(
                "news.http_error",
                source=self.source_slug,
                url=url,
                error=str(exc),
            )
            return None
        if resp.status_code >= 400:
            logger.warning(
                "news.bad_status",
                source=self.source_slug,
                url=url,
                status=resp.status_code,
            )
            return None
        return resp

    async def _throttle(self) -> None:
        min_delay = max(settings.scraper_min_delay_seconds, 1.0)
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < min_delay:
            await asyncio.sleep(min_delay - elapsed)
        self._last_request_at = time.monotonic()

    # ── Dedupe ───────────────────────────────────────────────────

    async def _should_fetch(self, url: str) -> bool:
        if self._redis is None:
            return True
        key = f"news:dedupe:{self.source_slug}:{url}"
        # SETNX with TTL — returns True only if the key wasn't set before.
        try:
            inserted = await self._redis.set(  # type: ignore[attr-defined]
                key, "1", ex=_DEDUPE_TTL_SECONDS, nx=True
            )
        except Exception as exc:
            # If Redis is unreachable, fall through and let the DB
            # UNIQUE constraint handle dedupe.
            logger.warning("news.dedupe_unreachable", error=str(exc))
            return True
        return bool(inserted)

    # ── Hooks for subclasses ─────────────────────────────────────

    async def list_article_urls(self) -> list[ArticleStub]:
        """Return recent article stubs. Implement in subclasses."""
        raise NotImplementedError

    def parse_article_body(self, html: str) -> str:
        """Extract the article's plain-text body from raw HTML.

        Default implementation: grab the most-frequent <article> /
        main-content selector. Subclasses override when the site has
        a known wrapper class.
        """
        soup = BeautifulSoup(html, "lxml")
        # Try semantic <article> first
        node = soup.find("article")
        if node is None:
            # Fallback: largest <div> with class containing "content"/"article"
            candidates = soup.find_all(
                "div",
                class_=lambda c: c is not None and ("content" in c or "article" in c),
            )
            if candidates:
                node = max(candidates, key=lambda n: len(n.get_text(strip=True)))
        if node is None:
            return ""
        # Strip script/style/aside/figure noise
        for junk in node.find_all(
            ["script", "style", "aside", "figure", "iframe", "nav"]
        ):
            junk.decompose()
        paragraphs = [
            p.get_text(strip=True) for p in node.find_all("p") if p.get_text(strip=True)
        ]
        return "\n\n".join(paragraphs)

    # ── Orchestration ────────────────────────────────────────────

    async def fetch_articles(self) -> AsyncIterator[NewsArticleRow]:
        """Yield fully-populated articles ready to persist."""
        try:
            stubs = await self.list_article_urls()
        except Exception as exc:
            logger.error(
                "news.list_failed",
                source=self.source_slug,
                error=str(exc),
            )
            return

        now = datetime.now(tz=timezone.utc)
        for stub in stubs:
            # Skip too-old articles
            age_days = (now - stub.published_at).days
            if age_days > _MAX_ARTICLE_AGE_DAYS:
                continue
            if not await self._should_fetch(stub.url):
                continue
            resp = await self._get(stub.url)
            if resp is None:
                continue
            try:
                body = self.parse_article_body(resp.text)
            except Exception as exc:
                logger.warning(
                    "news.body_parse_failed",
                    source=self.source_slug,
                    url=stub.url,
                    error=str(exc),
                )
                continue
            if not body or len(body) < 80:
                # Tiny "bodies" are usually paywalled stubs or
                # blockquotes — skip.
                continue
            yield NewsArticleRow(
                source=self.source_slug,
                url=stub.url,
                headline=stub.headline,
                body=body,
                published_at=stub.published_at,
            )


# ── Utilities subclasses share ───────────────────────────────────


def parse_rss_pubdate(value: str) -> datetime:
    """Parse RFC-822 pubDate strings ('Sat, 14 May 2026 09:00:00 +0500')
    to a UTC-aware datetime. Falls back to now() on malformed dates so
    a single junky item doesn't sink the whole feed."""
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_rss_feed(xml: str, source_slug: str) -> list[ArticleStub]:
    """Generic RSS 2.0 parser shared by all sources. Returns stubs in
    feed order; the caller can sort or trim by recency."""
    soup = BeautifulSoup(xml, "xml")
    items = soup.find_all("item")
    out: list[ArticleStub] = []
    for item in items:
        link_node = item.find("link")
        title_node = item.find("title")
        pub_node = item.find("pubDate")
        if not link_node or not title_node:
            continue
        url = link_node.get_text(strip=True)
        title = title_node.get_text(strip=True)
        if not url or not title:
            continue
        pub = parse_rss_pubdate(pub_node.get_text(strip=True)) if pub_node else datetime.now(tz=timezone.utc)
        out.append(ArticleStub(url=url, headline=title, published_at=pub))
    if not items:
        logger.warning("news.rss_empty", source=source_slug)
    return out
