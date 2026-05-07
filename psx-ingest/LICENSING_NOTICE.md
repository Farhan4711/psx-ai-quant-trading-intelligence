# PSX Market Data — Licensing Notice

> **Every file in this directory that fetches, stores, or processes PSX market data
> must include the following comment at the top of the file:**

```python
# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk
# Internal reference: psx-docs/adr/ADR-000-psx-data-licensing.md
# Before activating any paid feature or commercial redistribution, upgrade
# the license to Capital Stake API or direct PSX redistribution license.
```

---

## What this means in practice

| Action | Allowed under Path A? |
|---|---|
| Fetch EOD OHLCV from dps.psx.com.pk | Yes — non-commercial, rate-limited |
| Store raw data in our own database | Yes — for our own product's operation |
| Display data to authenticated users in our UI | Yes — non-commercial product |
| Export bulk raw OHLCV to users as a download | No — constitutes redistribution |
| Provide a public API that returns raw PSX prices | No — constitutes redistribution |
| Sell access to PSX data via a Pro tier | No — requires Path B or C license first |
| Charge users for using the analytics product | No — upgrade license before Phase 5 |

## Rate-limiting requirements

All scrapers targeting PSX or its affiliated portals must:

- Respect `robots.txt` — check it on every new deployment
- Wait at least **3 seconds** between requests to the same domain
- Run heavy backfill jobs during **off-peak hours** (midnight–6 AM PKT)
- Archive all raw HTTP responses to object storage before parsing
- Include a `User-Agent` header identifying the application:
  `User-Agent: [BUSINESS_NAME]-psx-data-ingest/1.0 (non-commercial; contact@[DOMAIN])`

## Review trigger

When the product transitions to paid tiers (Phase 5), this notice must be updated
to reflect the new licensing path and the above restrictions re-evaluated.

See: `psx-docs/adr/ADR-000-psx-data-licensing.md`
