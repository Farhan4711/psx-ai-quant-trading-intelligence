"""
News scrapers — Phase 3 data path.

Five sources are wired (Dawn Business, Business Recorder, Profit
Pakistan Today, The News Business, Tribune Business). Each source
module exposes a `Scraper` class that subclasses `BaseNewsScraper`
and implements `fetch_articles()`.

Top-level orchestration (which sources to run, how often) lives in
`psx_ingest/tasks/news.py`. Persistence + entity extraction +
sentiment scoring lives in `persistence.py` so the scrapers stay
focused on parsing.
"""
