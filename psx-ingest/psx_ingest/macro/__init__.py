"""
Macro indicator scrapers — fills the `macro_indicators` table that
the price-chart overlay + feature engineering pipeline read from.

Sources
-------
- SBP policy rate (sbp.org.pk) — set every ~8 weeks by MPC
- KIBOR 1m / 3m / 6m / 12m (sbp.org.pk/ecodata/kibor) — daily
- PKR/USD interbank rate (sbp.org.pk) — daily
- Brent / Gold deferred to a later step — they need a premium data
  source or scraping the SBP weekly bulletin PDFs
"""
