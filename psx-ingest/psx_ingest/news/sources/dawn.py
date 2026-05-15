"""
Dawn Business scraper — dawn.com/business.

Dawn publishes RSS feeds per section. The business feed is the
canonical signal for PSX-relevant macro, regulatory, and company news.

Feed: https://www.dawn.com/feeds/business
Site: https://www.dawn.com/business

Body wrappers
-------------
Dawn's article pages use the `.story__content` div (legacy `.content
article-content`). We try the semantic <article> tag first via the
base parser, then fall back to that class.
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


class DawnBusinessScraper(BaseNewsScraper):
    source_slug = "dawn"
    display_name = "Dawn Business"

    _FEED_URL = "https://www.dawn.com/feeds/business"

    async def list_article_urls(self) -> list[ArticleStub]:
        resp = await self._get(self._FEED_URL)
        if resp is None:
            return []
        stubs = parse_rss_feed(resp.text, source_slug=self.source_slug)
        logger.info("dawn.feed_parsed", count=len(stubs))
        return stubs

    def parse_article_body(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        # Try Dawn's known wrapper first
        story = soup.find("div", class_="story__content")
        if story is None:
            story = soup.find("div", class_="content article-content")
        if story is None:
            return super().parse_article_body(html)
        for junk in story.find_all(["script", "style", "aside", "figure", "iframe"]):
            junk.decompose()
        paras = [p.get_text(strip=True) for p in story.find_all("p")]
        return "\n\n".join(p for p in paras if p)
