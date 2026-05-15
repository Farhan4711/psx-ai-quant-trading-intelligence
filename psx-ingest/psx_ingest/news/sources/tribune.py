"""
Express Tribune Business scraper — tribune.com.pk/business.

Feed: https://tribune.com.pk/feed/business

Tribune is English-language with strong corporate coverage. Useful
because their headlines tend to be company-name-heavy which gives
the entity extractor easy hits.
"""

from __future__ import annotations

import structlog
from bs4 import BeautifulSoup

from psx_ingest.news.base import (
    ArticleStub,
    BaseNewsScraper,
    parse_rss_feed,
)

logger = structlog.get_logger(__name__)


class TribuneBusinessScraper(BaseNewsScraper):
    source_slug = "tribune"
    display_name = "Express Tribune (Business)"

    _FEED_URL = "https://tribune.com.pk/feed/business"

    async def list_article_urls(self) -> list[ArticleStub]:
        resp = await self._get(self._FEED_URL)
        if resp is None:
            return []
        stubs = parse_rss_feed(resp.text, source_slug=self.source_slug)
        logger.info("tribune.feed_parsed", count=len(stubs))
        return stubs

    def parse_article_body(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        # Tribune wraps articles in `.story-text` or `.story_main`
        story = soup.find("span", class_="story-text") or soup.find(
            "div", class_="story_main"
        )
        if story is None:
            return super().parse_article_body(html)
        for junk in story.find_all(["script", "style", "aside", "figure", "iframe"]):
            junk.decompose()
        paras = [p.get_text(strip=True) for p in story.find_all("p")]
        return "\n\n".join(p for p in paras if p)
