"""Dividend purification report (Phase 4 Step 65)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.community import PurificationRecord
from psx_api.models.portfolios import Portfolio, Transaction
from psx_api.models.securities import Security
from psx_api.purification.calculator import (
    DEFAULT_PURIFICATION_PCT,
    DividendRecord,
    compute_report,
)
from psx_api.timezone import today_pkt


class PurificationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def report(
        self,
        user_id: str,
        *,
        fiscal_year: int | None = None,
        purification_pct: Decimal | None = None,
    ) -> dict[str, Any]:
        fiscal_year = fiscal_year or today_pkt().year
        pct = purification_pct or DEFAULT_PURIFICATION_PCT

        # Pull dividend transactions for KMI-compliant symbols only
        rows = (
            await self._db.execute(
                select(
                    Transaction.symbol,
                    Transaction.transaction_date,
                    Transaction.quantity,
                    Transaction.price_per_share,
                )
                .join(Portfolio, Portfolio.id == Transaction.portfolio_id)
                .join(Security, Security.symbol == Transaction.symbol)
                .where(
                    Portfolio.user_id == user_id,
                    Transaction.transaction_type == "dividend",
                    Security.is_kmi_compliant.is_(True),
                )
            )
        ).all()

        dividends = [
            DividendRecord(
                symbol=r[0],
                transaction_date=r[1],
                amount_pkr=r[2] * r[3],
            )
            for r in rows
        ]

        report = compute_report(dividends, fiscal_year=fiscal_year, purification_pct=pct)

        # Pull existing donation marks for this user/year
        marks = (
            await self._db.execute(
                select(PurificationRecord.symbol, PurificationRecord.marked_donated_at).where(
                    PurificationRecord.user_id == user_id,
                    PurificationRecord.fiscal_year == fiscal_year,
                )
            )
        ).all()
        marked_set = {sym for sym, ts in marks if ts is not None}

        return {
            "fiscal_year": report.fiscal_year,
            "purification_pct": report.purification_pct,
            "total_dividends_pkr": report.total_dividends_pkr,
            "total_purification_pkr": report.total_purification_pkr,
            "lines": [
                {
                    "symbol": ln.symbol,
                    "dividends_pkr": ln.dividends_pkr,
                    "purification_pct": ln.purification_pct,
                    "purification_amount_pkr": ln.purification_amount_pkr,
                    "marked_donated": ln.symbol in marked_set,
                }
                for ln in report.lines
            ],
        }

    async def mark_donated(
        self, user_id: str, fiscal_year: int, symbol: str, *, donated: bool = True
    ) -> None:
        """Upsert a marked-donated record."""
        existing = (
            await self._db.execute(
                select(PurificationRecord).where(
                    PurificationRecord.user_id == user_id,
                    PurificationRecord.fiscal_year == fiscal_year,
                    PurificationRecord.symbol == symbol,
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.marked_donated_at = datetime.now(UTC) if donated else None
            await self._db.flush()
            return

        # Need to compute the line to know the amount + dividends_pkr
        report = await self.report(user_id, fiscal_year=fiscal_year)
        line = next((ln for ln in report["lines"] if ln["symbol"] == symbol), None)
        if not line:
            return  # nothing to mark

        record = PurificationRecord(
            user_id=user_id,
            fiscal_year=fiscal_year,
            symbol=symbol,
            dividends_received_pkr=line["dividends_pkr"],
            purification_pct=line["purification_pct"],
            purification_amount_pkr=line["purification_amount_pkr"],
            marked_donated_at=datetime.now(UTC) if donated else None,
        )
        self._db.add(record)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
