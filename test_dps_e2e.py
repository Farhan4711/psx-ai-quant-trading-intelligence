"""
End-to-end smoke test of the rewritten DpsScraper using the live /historical endpoint.
Run from the psx-ingest directory with:
    python -m pytest test_dps_e2e.py -v
or directly:
    python test_dps_e2e.py
"""
import asyncio
import sys
from datetime import date

# Allow running from the project root
sys.path.insert(0, r"C:\Users\Farhan Ul Haq\Desktop\PROJECT\psx-ai-trading-system\psx-ingest")

from psx_ingest.scrapers.dps import DpsScraper, OhlcvRow


async def main() -> None:
    print("=" * 60)
    print("DpsScraper E2E Test — POST /historical")
    print("=" * 60)

    async with DpsScraper(min_delay=2.0) as scraper:

        # ── Test 1: single date ───────────────────────────────────────────────
        print("\n[1] fetch_ohlcv('ENGRO', 2025-01-03)")
        rows = await scraper.fetch_ohlcv("ENGRO", date(2025, 1, 3))
        if rows:
            r = rows[0]
            print(f"    ✓  {r.symbol}  {r.date}  O={r.open}  H={r.high}  L={r.low}  C={r.close}  V={r.volume}")
        else:
            print("    ✗  No rows returned (date may be a holiday — try next business day)")

        # ── Test 2: range (one month) ─────────────────────────────────────────
        print("\n[2] fetch_ohlcv_range('HBL', 2025-01-01 → 2025-01-31)")
        rows = await scraper.fetch_ohlcv_range("HBL", date(2025, 1, 1), date(2025, 1, 31))
        print(f"    Rows returned: {len(rows)}")
        if rows:
            print(f"    First: {rows[0]}")
            print(f"    Last : {rows[-1]}")
            assert all(isinstance(r, OhlcvRow) for r in rows), "Not all OhlcvRow"
            assert all(r.symbol == "HBL" for r in rows), "Symbol mismatch"
            assert all(date(2025, 1, 1) <= r.date <= date(2025, 1, 31) for r in rows), "Date out of range"
            print("    ✓  All assertions passed")
        else:
            print("    ✗  No rows returned")

        # ── Test 3: unknown symbol → should return empty list, not crash ──────
        print("\n[3] fetch_ohlcv('XXXX_INVALID', 2025-01-03)")
        rows = await scraper.fetch_ohlcv("XXXX_INVALID", date(2025, 1, 3))
        print(f"    Rows returned: {len(rows)}  (expected 0)")
        assert len(rows) == 0, f"Expected empty list, got {rows}"
        print("    ✓  Empty list returned correctly")

        # ── Test 4: second real ticker ────────────────────────────────────────
        print("\n[4] fetch_ohlcv('LUCK', 2025-01-03)")
        rows = await scraper.fetch_ohlcv("LUCK", date(2025, 1, 3))
        if rows:
            r = rows[0]
            print(f"    ✓  {r.symbol}  {r.date}  O={r.open}  H={r.high}  L={r.low}  C={r.close}  V={r.volume}")
        else:
            print("    ✗  No rows (may be holiday)")

    print("\n" + "=" * 60)
    print("All tests completed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
