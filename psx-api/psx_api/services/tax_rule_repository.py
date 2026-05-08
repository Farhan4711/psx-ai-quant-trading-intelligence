"""
Loads tax_rules rows into the TaxBracket dataclasses consumed by
psx_api.tax.cgt. Cached aggressively because brackets only change when an
admin edits the table (typically once per Federal Budget cycle).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.tax_rules import TaxRule
from psx_api.tax.cgt import TaxBracket


class TaxRuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def load_cgt_brackets(self) -> list[TaxBracket]:
        result = await self._db.execute(
            select(TaxRule).where(TaxRule.rule_type == "cgt").order_by(TaxRule.effective_from)
        )
        rows = result.scalars().all()
        return [
            TaxBracket(
                effective_from=r.effective_from,
                effective_to=r.effective_to,
                is_filer=r.is_filer,
                min_holding_days=r.min_holding_days,
                max_holding_days=r.max_holding_days,
                rate_pct=r.rate_pct,
            )
            for r in rows
        ]
