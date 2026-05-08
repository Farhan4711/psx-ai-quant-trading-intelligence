"""
Macro indicators read service.

The actual ingestion (Step 47 daily worker pulling from SBP, OGRA, etc.)
is a Phase-2-D2 task — the **read** path is what the chart overlay UI
depends on, so we ship it now.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.macro import MacroIndicator


SUPPORTED_INDICATORS = [
    {"key": "kibor_1m", "label": "KIBOR 1M", "unit": "%", "category": "rates"},
    {"key": "kibor_3m", "label": "KIBOR 3M", "unit": "%", "category": "rates"},
    {"key": "kibor_6m", "label": "KIBOR 6M", "unit": "%", "category": "rates"},
    {"key": "kibor_12m", "label": "KIBOR 12M", "unit": "%", "category": "rates"},
    {
        "key": "sbp_policy_rate",
        "label": "SBP Policy Rate",
        "unit": "%",
        "category": "rates",
    },
    {"key": "pkr_usd", "label": "PKR/USD", "unit": "PKR", "category": "fx"},
    {"key": "brent_usd", "label": "Brent Crude (USD)", "unit": "USD", "category": "commodities"},
    {
        "key": "gold_pkr_per_tola",
        "label": "Gold (PKR/tola)",
        "unit": "PKR",
        "category": "commodities",
    },
]


class MacroService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_indicators(self) -> list[dict]:
        return SUPPORTED_INDICATORS

    async def series(
        self,
        indicator: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        q = select(MacroIndicator.date, MacroIndicator.value).where(
            MacroIndicator.indicator == indicator
        )
        if date_from:
            q = q.where(MacroIndicator.date >= date_from)
        if date_to:
            q = q.where(MacroIndicator.date <= date_to)
        q = q.order_by(MacroIndicator.date)
        rows = (await self._db.execute(q)).all()
        return [{"date": d.isoformat(), "value": float(v)} for d, v in rows]
