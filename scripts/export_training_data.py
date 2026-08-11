#!/usr/bin/env python3
"""
Export per-symbol training data to a Parquet file.

Phase 12 prep: pulls OHLCV + macro context from your local Postgres,
builds the same 23-feature vector that `psx_api.predictions.features`
computes for inference, plus a `y_next_day_up` binary label, and
writes one row per (symbol, date) where the warm-up windows are
satisfied.

The output Parquet lands at `data/training/psx_features.parquet`
(override via --out). Upload that single file to Google Drive; the
Colab notebook reads it directly.

Usage
-----
    # From the repo root, in your psx-api venv:
    python scripts/export_training_data.py
    python scripts/export_training_data.py --symbols HBL,UBL,ENGRO --out /tmp/sample.parquet
    python scripts/export_training_data.py --since 2021-01-01

Why a single Parquet file?
- Colab + Drive together choke on many small files (each is a
  separate HTTP call). One ~50MB Parquet uploads in seconds, loads
  in pandas in <1s.
- Parquet preserves per-column dtypes so the Colab notebook doesn't
  have to redo CSV type inference.

Sizing
- 84 active symbols × ~1250 trading days × 23 features × 8 bytes
  = ~20MB raw, ~5-10MB Parquet (snappy-compressed). Tiny.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add psx-api to import path so we can reuse the feature extractor.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "psx-api"))

import pandas as pd  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from psx_api.predictions.features import (  # noqa: E402
    FEATURE_NAMES,
    MarketContext,
    OhlcvBar,
    compute_features,
)


_DEFAULT_DB_URL = "postgresql+asyncpg://psx_user:psx_pass_dev@localhost:5433/psx_dev"
_DEFAULT_OUT = _REPO_ROOT / "data" / "training" / "psx_features.parquet"
_MIN_BARS_PER_SYMBOL = 80   # below this, feature warm-ups won't be satisfied


# ── DB loaders ────────────────────────────────────────────────────


async def _load_symbols(session: AsyncSession, only: list[str] | None) -> list[str]:
    if only:
        return [s.strip().upper() for s in only if s.strip()]
    rows = (
        await session.execute(
            text("SELECT symbol FROM securities WHERE is_active = TRUE ORDER BY symbol")
        )
    ).fetchall()
    return [r[0] for r in rows]


async def _load_bars(
    session: AsyncSession, symbol: str, since: date | None
) -> list[tuple[date, OhlcvBar]]:
    if since:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT date, open, high, low, close, volume
                    FROM ohlcv_daily
                    WHERE symbol = :symbol AND date >= :since
                    ORDER BY date ASC
                    """
                ),
                {"symbol": symbol, "since": since},
            )
        ).fetchall()
    else:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT date, open, high, low, close, volume
                    FROM ohlcv_daily
                    WHERE symbol = :symbol
                    ORDER BY date ASC
                    """
                ),
                {"symbol": symbol},
            )
        ).fetchall()
    return [
        (
            r[0],
            OhlcvBar(
                open=float(r[1]),
                high=float(r[2]),
                low=float(r[3]),
                close=float(r[4]),
                volume=float(r[5]),
            ),
        )
        for r in rows
    ]


async def _load_macro_by_date(session: AsyncSession) -> dict[date, dict[str, float]]:
    """All macro_indicators flattened to {date: {kibor_6m_pct, pkr_usd, ...}}.
    Cheap because the table is tiny (a few hundred rows per indicator)."""
    rows = (
        await session.execute(
            text("SELECT date, indicator, value FROM macro_indicators")
        )
    ).fetchall()
    out: dict[date, dict[str, float]] = {}
    for r in rows:
        out.setdefault(r[0], {})[r[1]] = float(r[2])
    return out


async def _load_kse100_returns(session: AsyncSession) -> dict[date, float]:
    """Compute %-day-change of the KSE100 index from ohlcv_daily.
    Falls back to an empty map if KSE100 isn't ingested yet (sets
    kse100_return_pct=None on those rows, which the model learns to
    handle as missing)."""
    rows = (
        await session.execute(
            text(
                """
                SELECT date, close
                FROM ohlcv_daily
                WHERE symbol = 'KSE100' OR symbol = 'KSE-100'
                ORDER BY date ASC
                """
            )
        )
    ).fetchall()
    out: dict[date, float] = {}
    prev_close: float | None = None
    for r in rows:
        close = float(r[1])
        if prev_close is not None and prev_close > 0:
            out[r[0]] = (close - prev_close) / prev_close * 100
        prev_close = close
    return out


# ── Per-symbol row builder ────────────────────────────────────────


def _rolling_features(
    bars_with_date: list[tuple[date, OhlcvBar]],
    macro_by_date: dict[date, dict[str, float]],
    kse100_returns: dict[date, float],
    *,
    symbol: str,
) -> list[dict]:
    """One row per bar (excluding warm-up + the last bar with no label).
    Each row has FEATURE_NAMES + symbol/date/y_next_day_up columns."""
    out: list[dict] = []
    n = len(bars_with_date)
    if n < _MIN_BARS_PER_SYMBOL + 1:
        return out

    # Pre-compute the y label as `close[t+1] > close[t]`.
    closes = [b.close for _, b in bars_with_date]

    for i in range(_MIN_BARS_PER_SYMBOL, n - 1):
        d, _ = bars_with_date[i]
        # Build the feature window ending at bar i.
        window = [b for _, b in bars_with_date[: i + 1]]
        macro = macro_by_date.get(d, {})
        ctx = MarketContext(
            kse100_return_pct=kse100_returns.get(d),
            sector_return_pct=None,  # filled in post-hoc per sector below
            kibor_6m_pct=macro.get("kibor_6m"),
            pkr_usd_change_pct=None,  # filled in post-hoc using prev-day pkr/usd
        )
        # PKR/USD % change vs previous business day, if both present.
        prev_d = bars_with_date[i - 1][0] if i > 0 else None
        if prev_d:
            cur_fx = macro.get("pkr_usd")
            prev_fx = macro_by_date.get(prev_d, {}).get("pkr_usd")
            if cur_fx and prev_fx and prev_fx > 0:
                ctx = MarketContext(
                    kse100_return_pct=ctx.kse100_return_pct,
                    sector_return_pct=ctx.sector_return_pct,
                    kibor_6m_pct=ctx.kibor_6m_pct,
                    pkr_usd_change_pct=(cur_fx - prev_fx) / prev_fx * 100,
                )

        feats = compute_features(window, ctx)
        # Skip rows where any non-context feature is None (warm-up unmet).
        core = [
            k
            for k in FEATURE_NAMES
            if k not in (
                "kse100_return_pct",
                "sector_return_pct",
                "kibor_6m_pct",
                "pkr_usd_change_pct",
            )
        ]
        if any(feats.get(k) is None for k in core):
            continue

        row = {"symbol": symbol, "date": d}
        for k in FEATURE_NAMES:
            row[k] = feats.get(k)
        row["y_next_day_up"] = 1 if closes[i + 1] > closes[i] else 0
        out.append(row)
    return out


# ── Main ──────────────────────────────────────────────────────────


async def run(args: argparse.Namespace) -> None:
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = os.environ.get("DATABASE_URL", _DEFAULT_DB_URL)

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    only = (args.symbols or "").split(",") if args.symbols else None
    since = date.fromisoformat(args.since) if args.since else None

    all_rows: list[dict] = []
    try:
        async with session_factory() as session:
            symbols = await _load_symbols(session, only)
            print(f"  → {len(symbols)} symbols to process")

            macro_by_date = await _load_macro_by_date(session)
            print(f"  → {len(macro_by_date)} macro dates loaded")

            kse100 = await _load_kse100_returns(session)
            print(f"  → {len(kse100)} KSE-100 return dates")

            for i, sym in enumerate(symbols, 1):
                bars = await _load_bars(session, sym, since)
                rows = _rolling_features(
                    bars, macro_by_date, kse100, symbol=sym
                )
                all_rows.extend(rows)
                print(
                    f"  [{i:>3}/{len(symbols)}] {sym}: "
                    f"{len(bars)} bars → {len(rows)} training rows"
                )
    finally:
        await engine.dispose()

    if not all_rows:
        print("\n  ⚠ No training rows produced. Did you run the EOD ingest?")
        return

    df = pd.DataFrame(all_rows)
    # Stable column order: symbol, date, features..., label
    cols = ["symbol", "date", *FEATURE_NAMES, "y_next_day_up"]
    df = df[cols]
    df.to_parquet(out_path, compression="snappy", index=False)
    print(f"\n  ✓ Wrote {len(df):,} rows × {len(cols)} cols → {out_path}")
    print(f"    File size: {out_path.stat().st_size / 1024:.1f} KB")
    print(f"    Class balance: y=1 {df['y_next_day_up'].mean() * 100:.1f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(_DEFAULT_OUT),
        help=f"Output Parquet path (default: {_DEFAULT_OUT})",
    )
    parser.add_argument(
        "--symbols",
        default=None,
        help="Comma-separated symbol filter (default: all active securities)",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Only include bars from this ISO date onward (YYYY-MM-DD)",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
