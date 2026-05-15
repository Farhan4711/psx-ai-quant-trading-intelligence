"""
Concrete news-source scrapers. Each module exposes a `Scraper` class.

`get_all_scrapers()` returns the list of all five so the orchestrator
task doesn't have to hard-code them.
"""

from __future__ import annotations

from psx_ingest.news.base import BaseNewsScraper
from psx_ingest.news.sources.brecorder import BusinessRecorderScraper
from psx_ingest.news.sources.dawn import DawnBusinessScraper
from psx_ingest.news.sources.profit import ProfitPakistanTodayScraper
from psx_ingest.news.sources.thenews import TheNewsBusinessScraper
from psx_ingest.news.sources.tribune import TribuneBusinessScraper


def get_all_scrapers() -> list[type[BaseNewsScraper]]:
    return [
        DawnBusinessScraper,
        BusinessRecorderScraper,
        ProfitPakistanTodayScraper,
        TheNewsBusinessScraper,
        TribuneBusinessScraper,
    ]


__all__ = [
    "BusinessRecorderScraper",
    "DawnBusinessScraper",
    "ProfitPakistanTodayScraper",
    "TheNewsBusinessScraper",
    "TribuneBusinessScraper",
    "get_all_scrapers",
]
