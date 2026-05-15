"""
Business Recorder scraper — brecorder.com.

Business Recorder is Pakistan's oldest financial daily — the most
PSX-specific source by volume. The "markets" and "business" sections
together cover corporate announcements, sector news, and currency
moves.

Feed: https://www.brecorder.com/feeds/latest-news
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


class BusinessRecorderScraper(BaseNewsScraper):
    source_slug = "brecorder"
    display_name = "Business Recorder"

    _FEEDS = [
        # Latest-news covers markets + business; we filter post-hoc by
        # mention extraction so a single feed is enough.
        "https://www.brecorder.com/feeds/latest-news",
    ]

    async def list_article_urls(self) -> list[ArticleStub]:
        stubs: list[ArticleStub] = []
        for url in self._FEEDS:
            resp = await self._get(url)
            if resp is None:
                continue
            stubs.extend(parse_rss_feed(resp.text, source_slug=self.source_slug))
        logger.info("brecorder.feeds_parsed", count=len(stubs))
        return stubs

    def parse_article_body(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        # brecorder wraps articles in <div class="story-detail">
        story = soup.find("div", class_="story-detail")
        if story is None:
            return super().parse_article_body(html)
        for junk in story.find_all(["script", "style", "aside", "figure", "iframe"]):
            junk.decompose()
        paras = [p.get_text(strip=True) for p in story.find_all("p")]
        return "\n\n".join(p for p in paras if p)
