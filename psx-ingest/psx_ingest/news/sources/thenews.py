"""
The News International — business section scraper.

Site: thenews.com.pk/latest/category/business
Feed: https://www.thenews.com.pk/rss/2/3   (business category)

The News mixes wire-service and original reporting. Useful primarily
for cross-referencing big stories (when 4 of 5 sources carry the same
headline, mention extraction picks the symbol up reliably).
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


class TheNewsBusinessScraper(BaseNewsScraper):
    source_slug = "thenews"
    display_name = "The News International (Business)"

    _FEED_URL = "https://www.thenews.com.pk/rss/2/3"

    async def list_article_urls(self) -> list[ArticleStub]:
        resp = await self._get(self._FEED_URL)
        if resp is None:
            return []
        stubs = parse_rss_feed(resp.text, source_slug=self.source_slug)
        logger.info("thenews.feed_parsed", count=len(stubs))
        return stubs

    def parse_article_body(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        # The News uses `.story-detail` or `.detail-content`
        story = soup.find("div", class_="detail-content") or soup.find("div", class_="story-detail")
        if story is None:
            return super().parse_article_body(html)
        for junk in story.find_all(["script", "style", "aside", "figure", "iframe"]):
            junk.decompose()
        paras = [p.get_text(strip=True) for p in story.find_all("p")]
        return "\n\n".join(p for p in paras if p)
