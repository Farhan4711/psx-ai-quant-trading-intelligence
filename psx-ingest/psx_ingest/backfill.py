# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
CLI entrypoint for the one-time 5-year OHLCV backfill.

Usage:
    # Full backfill (all active symbols, 5 years)
    python -m psx_ingest.backfill

    # Specific symbols only
    python -m psx_ingest.backfill --symbols ENGRO,LUCK,PSO

    # Custom date range
    python -m psx_ingest.backfill --from 2020-01-01 --to 2024-12-31

    # Re-run even if data already exists (force mode)
    python -m psx_ingest.backfill --no-skip-existing

LICENSING NOTE (ADR-000):
  Backfills must run off-peak (22:00–06:00 PKT).
  The scraper enforces a 3-second minimum delay between requests.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date

import structlog

from psx_ingest.tasks.backfill import _run_backfill

logger = structlog.get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m psx_ingest.backfill",
        description="Backfill 5 years of PSX OHLCV history from DPS",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of symbols (default: all active)",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Start date (default: 5 years ago)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="End date (default: today PKT)",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        default=True,
        help="Re-fetch even if symbol already has sufficient history",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else None

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )

    logger.info(
        "Starting backfill",
        symbols=symbols or "all active",
        from_date=(args.from_date or "default (5y ago)"),
        to_date=(args.to_date or "default (today)"),
        skip_existing=args.skip_existing,
    )

    result = await _run_backfill(
        symbols=symbols,
        from_date=args.from_date,
        to_date=args.to_date,
        skip_existing=args.skip_existing,
    )

    logger.info("Done", **result)

    if result["symbols_err"] > 0:
        logger.warning(
            "Some symbols failed",
            failed=result["symbols_err"],
            hint="Re-run with --no-skip-existing to retry all, or pass --symbols <list>",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
