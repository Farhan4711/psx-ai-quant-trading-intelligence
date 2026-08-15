"""
Compute per-bucket peer aggregates from opted-in users.

Algorithm
---------
1. Pull all users with `share_anonymously=true`, their DOB, risk
   archetype, and portfolio market value.
2. Bucket each user into (archetype, age_bucket, size_bucket).
3. For each non-empty bucket with `>= MIN_BUCKET_SAMPLES` members:
   - Compute median YTD return % across members
   - Compute top-10 holdings (by frequency across members)
   - Compute median sector allocation
4. Upsert into `peer_aggregates`.

Bucket suppression
------------------
The read path also enforces `sample_count >= 5`, so even if a bucket
slips through here with sample_count=3 the user-facing panel hides
it. We persist any bucket with size > 0 for ops visibility but the
read side is the privacy floor.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.config import settings
from psx_ingest.timezone import today_pkt

logger = structlog.get_logger(__name__)


MIN_BUCKET_SAMPLES = 5  # k-anonymity floor (matches psx_api/benchmark/buckets.py)


# ── Bucketing (mirrors psx_api/benchmark/buckets.py) ─────────────


def _age_bucket(dob: date | None, today: date) -> str:
    if dob is None:
        return "unknown"
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if years < 25:
        return "18-24"
    if years < 35:
        return "25-34"
    if years < 45:
        return "35-44"
    if years < 55:
        return "45-54"
    return "55+"


def _size_bucket(value_pkr: float | None) -> str:
    if value_pkr is None:
        return "unknown"
    if value_pkr < 100_000:
        return "<100K"
    if value_pkr < 500_000:
        return "100K-500K"
    if value_pkr < 2_000_000:
        return "500K-2M"
    if value_pkr < 10_000_000:
        return "2M-10M"
    return "10M+"


@dataclass(slots=True)
class UserSample:
    user_id: str
    archetype: str
    age_bucket: str
    size_bucket: str
    ytd_return_pct: float | None
    top_holdings: list[str]
    sector_allocation: dict[str, float]


@dataclass(slots=True)
class AggregateSummary:
    users_considered: int = 0
    buckets_written: int = 0
    buckets_suppressed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "users_considered": self.users_considered,
            "buckets_written": self.buckets_written,
            "buckets_suppressed": self.buckets_suppressed,
        }


# ── Loaders ─────────────────────────────────────────────────────


async def _load_samples(session: AsyncSession) -> list[UserSample]:
    """One row per opted-in user with current portfolio shape."""
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    u.id,
                    COALESCE(u.risk_archetype, 'unknown') AS archetype,
                    u.date_of_birth
                FROM users u
                WHERE u.share_anonymously = TRUE
                """
            )
        )
    ).fetchall()

    today = today_pkt()
    samples: list[UserSample] = []
    for r in rows:
        user_id = r[0]
        archetype = r[1]
        dob = r[2]
        portfolio = await _summarise_portfolio(session, user_id)
        samples.append(
            UserSample(
                user_id=user_id,
                archetype=archetype,
                age_bucket=_age_bucket(dob, today),
                size_bucket=_size_bucket(portfolio["market_value_pkr"]),
                ytd_return_pct=portfolio["ytd_return_pct"],
                top_holdings=portfolio["top_holdings"],
                sector_allocation=portfolio["sector_allocation"],
            )
        )
    return samples


async def _summarise_portfolio(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Compact portfolio shape we need for bucketing + aggregation.

    All math is done in SQL where it's a hot path; this function only
    coordinates the queries. If the user has no portfolio yet,
    everything is None / empty so they bucket into <100K.
    """
    # Total market value via the latest close of each holding × qty.
    mv_row = (
        await session.execute(
            text(
                """
                SELECT COALESCE(SUM(h.quantity * o.close), 0) AS mv
                FROM holdings_snapshot h
                JOIN LATERAL (
                    SELECT close FROM ohlcv_daily
                    WHERE symbol = h.symbol
                    ORDER BY date DESC LIMIT 1
                ) o ON TRUE
                JOIN portfolios p ON p.id = h.portfolio_id
                WHERE p.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        )
    ).fetchone()
    market_value = float(mv_row[0]) if mv_row and mv_row[0] is not None else 0.0
    if market_value <= 0:
        return {
            "market_value_pkr": None,
            "ytd_return_pct": None,
            "top_holdings": [],
            "sector_allocation": {},
        }

    # YTD return: ((current_value - jan1_value) / jan1_value) * 100,
    # where jan1_value is the holdings × Jan-1 close. Cheap-and-cheerful
    # approximation — ignores intra-year flows.
    jan1 = date(today_pkt().year, 1, 1)
    jan1_row = (
        await session.execute(
            text(
                """
                SELECT COALESCE(SUM(h.quantity * o.close), 0)
                FROM holdings_snapshot h
                JOIN LATERAL (
                    SELECT close FROM ohlcv_daily
                    WHERE symbol = h.symbol AND date <= :jan1
                    ORDER BY date DESC LIMIT 1
                ) o ON TRUE
                JOIN portfolios p ON p.id = h.portfolio_id
                WHERE p.user_id = :user_id
                """
            ),
            {"user_id": user_id, "jan1": jan1},
        )
    ).fetchone()
    jan1_value = float(jan1_row[0]) if jan1_row and jan1_row[0] is not None else 0.0
    ytd_return = (market_value - jan1_value) / jan1_value * 100 if jan1_value > 0 else None

    # Top holdings + sector allocation.
    holdings = (
        await session.execute(
            text(
                """
                SELECT h.symbol, s.sector, (h.quantity * o.close) AS mv
                FROM holdings_snapshot h
                JOIN securities s ON s.symbol = h.symbol
                JOIN LATERAL (
                    SELECT close FROM ohlcv_daily
                    WHERE symbol = h.symbol
                    ORDER BY date DESC LIMIT 1
                ) o ON TRUE
                JOIN portfolios p ON p.id = h.portfolio_id
                WHERE p.user_id = :user_id
                ORDER BY mv DESC
                """
            ),
            {"user_id": user_id},
        )
    ).fetchall()

    top_symbols = [h[0] for h in holdings[:10]]

    sector_mv: defaultdict[str, float] = defaultdict(float)
    for _, sector, mv in holdings:
        sector_mv[sector or "unknown"] += float(mv or 0.0)
    sector_allocation = {s: round(mv / market_value * 100, 2) for s, mv in sector_mv.items()}

    return {
        "market_value_pkr": market_value,
        "ytd_return_pct": round(ytd_return, 4) if ytd_return is not None else None,
        "top_holdings": top_symbols,
        "sector_allocation": sector_allocation,
    }


# ── Aggregator ──────────────────────────────────────────────────


def _aggregate_bucket(samples: list[UserSample]) -> dict[str, Any]:
    """One bucket → one row payload (excluding key columns)."""
    ytd = [s.ytd_return_pct for s in samples if s.ytd_return_pct is not None]
    median_ytd = round(statistics.median(ytd), 4) if ytd else None

    holdings_counter: Counter[str] = Counter()
    for s in samples:
        holdings_counter.update(s.top_holdings)
    top10 = [{"symbol": sym, "frequency": count} for sym, count in holdings_counter.most_common(10)]

    # Median sector weight across members.
    sector_weights: defaultdict[str, list[float]] = defaultdict(list)
    for s in samples:
        for sector, pct in s.sector_allocation.items():
            sector_weights[sector].append(pct)
    sector_alloc = [
        {"sector": sec, "median_pct": round(statistics.median(weights), 2)}
        for sec, weights in sorted(sector_weights.items())
    ]

    return {
        "sample_count": len(samples),
        "median_ytd_return_pct": median_ytd,
        "top_holdings": top10,
        "sector_allocation": sector_alloc,
    }


# ── Persistence ─────────────────────────────────────────────────


async def _upsert_bucket(
    session: AsyncSession,
    key: tuple[str, str, str],
    payload: dict[str, Any],
) -> None:
    archetype, age, size = key
    import json

    await session.execute(
        text(
            """
            INSERT INTO peer_aggregates
                (archetype, age_bucket, size_bucket,
                 sample_count, median_ytd_return_pct,
                 top_holdings, sector_allocation, computed_at)
            VALUES
                (:archetype, :age, :size,
                 :sample_count, :median_ytd,
                 CAST(:top_holdings AS JSONB),
                 CAST(:sector_allocation AS JSONB),
                 NOW())
            ON CONFLICT (archetype, age_bucket, size_bucket)
            DO UPDATE SET
                sample_count         = EXCLUDED.sample_count,
                median_ytd_return_pct= EXCLUDED.median_ytd_return_pct,
                top_holdings         = EXCLUDED.top_holdings,
                sector_allocation    = EXCLUDED.sector_allocation,
                computed_at          = NOW()
            """
        ),
        {
            "archetype": archetype,
            "age": age,
            "size": size,
            "sample_count": payload["sample_count"],
            "median_ytd": payload["median_ytd_return_pct"],
            "top_holdings": json.dumps(payload["top_holdings"]),
            "sector_allocation": json.dumps(payload["sector_allocation"]),
        },
    )


# ── Orchestration ───────────────────────────────────────────────


async def run_aggregation() -> AggregateSummary:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    summary = AggregateSummary()
    try:
        async with session_factory() as session:
            samples = await _load_samples(session)
            summary.users_considered = len(samples)

            grouped: defaultdict[tuple[str, str, str], list[UserSample]] = defaultdict(list)
            for s in samples:
                grouped[(s.archetype, s.age_bucket, s.size_bucket)].append(s)

            for key, members in grouped.items():
                payload = _aggregate_bucket(members)
                if payload["sample_count"] < MIN_BUCKET_SAMPLES:
                    summary.buckets_suppressed += 1
                    continue
                await _upsert_bucket(session, key, payload)
                summary.buckets_written += 1

            await session.commit()
    finally:
        await engine.dispose()

    logger.info(
        "benchmark.aggregate_complete",
        **summary.as_dict(),
    )
    return summary
