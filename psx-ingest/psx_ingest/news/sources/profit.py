"""
Profit Pakistan Today scraper — profit.pakistantoday.com.pk.

Profit is the business vertical of Pakistan Today, WordPress-backed,
so a standard `/feed/` RSS endpoint exists. Profit publishes deeper
analytical pieces than the dailies — good signal for guidance/M&A
commentary.

Feed: https://profit.pakistantoday.com.pk/feed/
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


class ProfitPakistanTodayScraper(BaseNewsScraper):
    source_slug = "profit"
    display_name = "Profit Pakistan Today"

    _FEED_URL = "https://profit.pakistantoday.com.pk/feed/"

    async def list_article_urls(self) -> list[ArticleStub]:
        resp = await self._get(self._FEED_URL)
        if resp is None:
            return []
        stubs = parse_rss_feed(resp.text, source_slug=self.source_slug)
        logger.info("profit.feed_parsed", count=len(stubs))
        return stubs

    def parse_article_body(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        # WordPress default — `.entry-content` is the article body
        story = soup.find("div", class_="entry-content")
        if story is None:
            story = soup.find("div", class_="td-post-content")
        if story is None:
            return super().parse_article_body(html)
        for junk in story.find_all(
            ["script", "style", "aside", "figure", "iframe", "div"],
            class_=lambda c: c is not None and "share" in c,
        ):
            junk.decompose()
        paras = [p.get_text(strip=True) for p in story.find_all("p")]
        return "\n\n".join(p for p in paras if p)
