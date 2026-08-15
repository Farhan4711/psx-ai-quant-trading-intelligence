"""
Benchmark service — anonymized peer comparison (Phase 4 Steps 60-61).

Read path is what the UI hits live: bucket the user, look up the matching
peer_aggregates row, return a panel payload. Aggregation is a separate
nightly job (not implemented in v1 — sample counts will be 0 until the
deploy + cron land).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.benchmark.buckets import (
    MIN_BUCKET_SAMPLES,
    age_bucket,
    archetype_bucket,
    bucket_label,
    size_bucket,
)
from psx_api.models.community import PeerAggregate
from psx_api.models.portfolios import Portfolio
from psx_api.models.users import User
from psx_api.services.portfolio_summary_service import PortfolioSummaryService


class BenchmarkService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def panel(self, user: User) -> dict[str, Any]:
        # Compute current portfolio value + sector mix for the user
        portfolios = (
            (await self._db.execute(select(Portfolio).where(Portfolio.user_id == user.id)))
            .scalars()
            .all()
        )
        if not portfolios:
            return {
                "available": False,
                "message": (
                    "You don't have a portfolio yet. "
                    "Start tracking trades to see how you compare."
                ),
            }

        # Sum portfolio value across all of the user's portfolios
        portfolio_value = Decimal("0")
        ytd_return = Decimal("0")
        invested = Decimal("0")
        sector_totals: dict[str, Decimal] = {}

        summary_service = PortfolioSummaryService(self._db)
        for p in portfolios:
            data = await summary_service.summary(p, is_filer=user.is_filer)
            portfolio_value += data["current_value_pkr"]
            invested += data["total_invested_pkr"]
            ytd_return += Decimal(str(data["unrealized_pnl_pkr"]))
            for row in data["sector_allocation"]:
                sector_totals[row["sector"]] = (
                    sector_totals.get(row["sector"], Decimal("0")) + row["value_pkr"]
                )

        ytd_pct = (ytd_return / invested * 100) if invested > 0 else Decimal("0")
        # User's top sector
        if sector_totals and portfolio_value > 0:
            top_sector, top_val = max(sector_totals.items(), key=lambda kv: kv[1])
            top_sector_pct = float(top_val / portfolio_value * 100)
        else:
            top_sector, top_sector_pct = None, None

        # Determine the bucket
        arch = archetype_bucket(user.risk_archetype)
        age = age_bucket(user.date_of_birth)
        size = size_bucket(portfolio_value)
        label = bucket_label(arch, age, size)

        agg = (
            await self._db.execute(
                select(PeerAggregate).where(
                    PeerAggregate.archetype == arch,
                    PeerAggregate.age_bucket == age,
                    PeerAggregate.size_bucket == size,
                )
            )
        ).scalar_one_or_none()

        if not agg or agg.sample_count < MIN_BUCKET_SAMPLES:
            return {
                "available": False,
                "bucket_label": label,
                "sample_count": agg.sample_count if agg else 0,
                "user_ytd_return_pct": float(ytd_pct),
                "user_top_sector": top_sector,
                "user_top_sector_pct": top_sector_pct,
                "message": (
                    f"Need at least {MIN_BUCKET_SAMPLES} peers in your bucket "
                    "to show comparisons. Invite friends to join — anonymized "
                    "data is opt-in only."
                ),
            }

        median_ytd = (
            float(agg.median_ytd_return_pct) if agg.median_ytd_return_pct is not None else None
        )
        # Percentile rank: where does the user sit?
        # Without a full distribution we approximate: above median → ~75th, below → ~25th
        if median_ytd is not None:
            if float(ytd_pct) > median_ytd:
                pct_rank = 60 + min(35, int(abs(float(ytd_pct) - median_ytd)))
            else:
                pct_rank = max(5, 40 - int(abs(median_ytd - float(ytd_pct))))
        else:
            pct_rank = None

        # Peer top sector
        peer_sectors = sorted(
            agg.sector_allocation or [],
            key=lambda r: r.get("pct", 0),
            reverse=True,
        )
        peer_top_sector = peer_sectors[0]["sector"] if peer_sectors else None
        peer_top_sector_pct = float(peer_sectors[0]["pct"]) if peer_sectors else None

        return {
            "available": True,
            "bucket_label": label,
            "sample_count": agg.sample_count,
            "user_ytd_return_pct": float(ytd_pct),
            "median_ytd_return_pct": median_ytd,
            "percentile_rank": pct_rank,
            "user_top_sector": top_sector,
            "user_top_sector_pct": top_sector_pct,
            "peer_top_sector": peer_top_sector,
            "peer_top_sector_pct": peer_top_sector_pct,
            "peer_top_holdings": agg.top_holdings or [],
        }
