"""
Sector-level views: side-by-side comparison with percentile ranks, and the
heatmap rollup (mcap + day change for every active stock by sector).

Percentile rank is "better than X% of the sector" — for ratios where higher
is better (ROE, dividend yield) the rank is the percentile of the value;
for "lower is better" ratios (P/E, P/B, debt/equity) we invert.

For v1 we use only the data we have on `securities` (mcap, KMI flag) plus
latest OHLCV (last close + prev close for day change). True fundamentals
(P/E, P/B, ROE) plug in here in Phase 2 once the financial-statements
ingestor lands; the schema already accepts them as optional.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.ohlcv import OhlcvDaily
from psx_api.models.securities import Security


_TWO = Decimal("0.01")
_HUNDRED = Decimal("100")


class SectorService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Compare ──────────────────────────────────────────────────

    async def compare(self, sector: str, symbols: list[str]) -> dict:
        symbols = [s.upper().strip() for s in symbols if s.strip()]
        if not symbols:
            return {"sector": sector, "items": [], "metric_definitions": _METRICS}

        # Pull selected stocks + every stock in the sector for percentile maths
        sector_rows = (
            await self._db.execute(
                select(Security).where(
                    Security.sector == sector, Security.is_active.is_(True)
                )
            )
        ).scalars().all()
        sector_universe = {s.symbol: s for s in sector_rows}

        # Latest 2 closes per requested symbol
        last_close, prev_close = await self._latest_two_closes(symbols)

        items: list[dict] = []
        for sym in symbols:
            sec = sector_universe.get(sym)
            if not sec:
                items.append({
                    "symbol": sym,
                    "company_name": None,
                    "missing": True,
                    "reason": f"{sym} is not in the {sector} sector or is inactive.",
                })
                continue
            lc = last_close.get(sym)
            pc = prev_close.get(sym)
            day_change_pct = (
                (((lc - pc) / pc) * _HUNDRED).quantize(_TWO)
                if lc is not None and pc is not None and pc != 0
                else None
            )
            metrics = {
                "market_cap_pkr": _opt_int(sec.market_cap_pkr),
                "last_close": _opt_dec(lc),
                "day_change_pct": _opt_dec(day_change_pct),
                # Phase 2 fundamentals — placeholders for now
                "pe_ratio": None,
                "pb_ratio": None,
                "roe": None,
                "dividend_yield": None,
                "debt_to_equity": None,
                "payout_ratio": None,
            }
            items.append({
                "symbol": sym,
                "company_name": sec.company_name,
                "is_kmi_compliant": sec.is_kmi_compliant,
                "missing": False,
                "metrics": metrics,
                "ranks": self._compute_ranks(sec, sector_universe),
            })

        return {
            "sector": sector,
            "constituent_count": len(sector_universe),
            "items": items,
            "metric_definitions": _METRICS,
        }

    # ── Heatmap ──────────────────────────────────────────────────

    async def heatmap(self, sector: str | None = None) -> list[dict]:
        q = select(Security).where(Security.is_active.is_(True))
        if sector:
            q = q.where(Security.sector == sector)
        rows = (await self._db.execute(q)).scalars().all()
        if not rows:
            return []

        symbols = [r.symbol for r in rows]
        last_close, prev_close = await self._latest_two_closes(symbols)

        out: list[dict] = []
        for r in rows:
            lc = last_close.get(r.symbol)
            pc = prev_close.get(r.symbol)
            day_change_pct = (
                float((lc - pc) / pc * 100)
                if lc is not None and pc is not None and pc != 0
                else None
            )
            out.append({
                "symbol": r.symbol,
                "company_name": r.company_name,
                "sector": r.sector,
                "is_kmi_compliant": r.is_kmi_compliant,
                "market_cap_pkr": int(r.market_cap_pkr) if r.market_cap_pkr else None,
                "last_close": float(lc) if lc is not None else None,
                "day_change_pct": day_change_pct,
            })
        # Sort by mcap desc — UI uses this directly for treemap layout
        out.sort(key=lambda d: d["market_cap_pkr"] or 0, reverse=True)
        return out

    # ── Internals ────────────────────────────────────────────────

    async def _latest_two_closes(
        self, symbols: list[str]
    ) -> tuple[dict[str, Decimal | None], dict[str, Decimal | None]]:
        rn = (
            func.row_number()
            .over(partition_by=OhlcvDaily.symbol, order_by=OhlcvDaily.date.desc())
            .label("rn")
        )
        subq = (
            select(OhlcvDaily.symbol, OhlcvDaily.close, rn)
            .where(OhlcvDaily.symbol.in_(symbols))
            .subquery()
        )
        rows = (
            await self._db.execute(
                select(subq.c.symbol, subq.c.close, subq.c.rn).where(subq.c.rn <= 2)
            )
        ).all()
        last: dict[str, Decimal | None] = {}
        prev: dict[str, Decimal | None] = {}
        for sym, close, rn_val in rows:
            v = Decimal(str(close)) if close is not None else None
            if rn_val == 1:
                last[sym] = v
            elif rn_val == 2:
                prev[sym] = v
        return last, prev

    @staticmethod
    def _compute_ranks(target: Security, universe: dict[str, Security]) -> dict:
        """For metrics we have today: market_cap percentile within the sector."""
        mcaps = sorted(
            [s.market_cap_pkr for s in universe.values() if s.market_cap_pkr is not None]
        )
        if target.market_cap_pkr is None or not mcaps:
            return {"market_cap": None}
        # percentile = fraction below target
        below = sum(1 for v in mcaps if v < target.market_cap_pkr)
        pct = round((below / len(mcaps)) * 100)
        return {"market_cap": pct}


# ── Metric metadata for the UI ──────────────────────────────────────────


_METRICS: list[dict] = [
    {"key": "market_cap_pkr", "label": "Market Cap (PKR)", "format": "mcap", "rankable": True, "rank_higher_is_better": True},
    {"key": "last_close", "label": "Last Close (PKR)", "format": "price", "rankable": False},
    {"key": "day_change_pct", "label": "Day Change %", "format": "pct", "rankable": False},
    {"key": "pe_ratio", "label": "P/E", "format": "decimal", "rankable": True, "rank_higher_is_better": False},
    {"key": "pb_ratio", "label": "P/B", "format": "decimal", "rankable": True, "rank_higher_is_better": False},
    {"key": "roe", "label": "ROE", "format": "pct", "rankable": True, "rank_higher_is_better": True},
    {"key": "dividend_yield", "label": "Dividend Yield", "format": "pct", "rankable": True, "rank_higher_is_better": True},
    {"key": "debt_to_equity", "label": "Debt / Equity", "format": "decimal", "rankable": True, "rank_higher_is_better": False},
    {"key": "payout_ratio", "label": "Payout Ratio", "format": "pct", "rankable": True, "rank_higher_is_better": False},
]


def _opt_dec(v: Decimal | None) -> str | None:
    return str(v) if v is not None else None


def _opt_int(v: int | None) -> int | None:
    return int(v) if v is not None else None
