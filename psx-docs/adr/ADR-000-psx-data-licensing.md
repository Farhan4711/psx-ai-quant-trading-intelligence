# ADR-000: PSX Market Data Licensing Strategy

**Date:** 2026-05-07
**Status:** Accepted
**Deciders:** [BUSINESS_NAME] founding team

---

## Context

The Pakistan Stock Exchange (PSX) explicitly prohibits commercial use of its market data without a license. The product requires end-of-day (EOD) OHLCV data, corporate actions, and index constituent lists for all ~500 listed securities.

Three paths are available:

| Path | Description | Timeline | Cost |
|---|---|---|---|
| A | Educational / non-commercial using DPS EOD portal | Immediate | Free |
| B | Capital Stake API (authorized PSX vendor) | Days–weeks | TBD via contract |
| C | Direct PSX market data redistribution license | Weeks–months | TBD via contract |

## Decision

**We choose Path A at launch.**

- The product launches as a free, educational, non-commercial tool.
- EOD data will be sourced from PSX's public Data Publishing System portal (`dps.psx.com.pk`), which provides historical EOD data in a format acceptable for non-commercial use.
- Contact has been initiated with PSX Market Data team (`marketdatarequest@psx.com.pk`) to establish the relationship and clarify the exact boundary of non-commercial use in writing.
- When the product begins charging users (Phase 5), we will upgrade to Path B (Capital Stake) or Path C (direct license) before the first paying transaction processes.

## Rationale

- Path A unblocks development immediately at zero marginal data cost.
- Capital Stake pricing is unknown until direct contact; committing to it before we have users would be premature.
- The direct PSX license (Path C) is the long-term correct answer but takes weeks to negotiate — the relationship is being started in parallel.
- The free-product framing is legitimate and protects the entity from licensing liability during the build phase.

## Consequences

### Constraints imposed by this decision

1. **No real-time or intraday data in Phase 1.** DPS provides EOD only. All price displays in Phase 1 will show the prior day's closing price during market hours, with a visible label: "Last close — real-time data available in a future release."
2. **Every ingest script must carry the licensing notice** (see `psx-ingest/LICENSING_NOTICE.md`). No exceptions.
3. **No commercial redistribution of raw data.** Users can see their own portfolio data and aggregated analytics. No bulk data export or API access that would allow downstream redistribution of raw PSX data.
4. **Upgrade trigger:** When any paid tier is activated, licensing must be upgraded to Path B or C before the first charge is processed. This is a hard gate in the Phase 5 checklist.
5. **DPS scraping limits:** The DPS portal is scraped with conservative rate limits (max 1 request per 3 seconds, off-peak hours preferred, `robots.txt` checked and respected on every deployment). Raw responses are archived to object storage so data can be re-parsed without re-scraping.

## Review Date

Re-evaluate at Phase 4 kickoff (approximately when the first paying customers are being onboarded) or earlier if PSX contacts us in response to the outreach email.

---

*This ADR follows the format described in Michael Nygard's "Documenting Architecture Decisions."*
