"""
Filer-vs-non-filer simulator.

Re-runs the user's portfolio transaction history through the existing
tax engine TWICE — once as filer, once as non-filer — and surfaces the
delta as a single number: "by becoming a tax filer, you would have kept
an additional PKR X last year." This is genuine social good and a viral
feature per the build plan.

Period: trailing 12 months by default; the UI exposes a date-range
override. Walks every sell transaction across every portfolio the user
owns, matches against open buy lots FIFO, computes CGT under each filer
status, sums the two results.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.portfolios import Portfolio, Transaction
from psx_api.services.tax_rule_repository import TaxRuleRepository
from psx_api.tax.cgt import BuyLot, NoApplicableTaxRuleError, TaxBracket, match_fifo
from psx_api.timezone import today_pkt

_TWO = Decimal("0.01")


class TaxSimulatorService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._tax_repo = TaxRuleRepository(db)

    async def simulate(
        self,
        user_id: str,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        date_to = date_to or today_pkt()
        date_from = date_from or (date_to - timedelta(days=365))

        portfolios = (
            (await self._db.execute(select(Portfolio).where(Portfolio.user_id == user_id)))
            .scalars()
            .all()
        )

        if not portfolios:
            return self._empty_result(date_from, date_to)

        brackets = await self._tax_repo.load_cgt_brackets()

        # Aggregate across all portfolios
        total_gross_gain = Decimal("0")
        total_brokerage = Decimal("0")
        total_fed = Decimal("0")
        total_cvt = Decimal("0")
        cgt_filer_total = Decimal("0")
        cgt_nonfiler_total = Decimal("0")
        sells_processed = 0

        for portfolio in portfolios:
            f, nf, gg, b, fed, cvt, count = await self._simulate_portfolio(
                portfolio,
                brackets,
                date_from=date_from,
                date_to=date_to,
            )
            cgt_filer_total += f
            cgt_nonfiler_total += nf
            total_gross_gain += gg
            total_brokerage += b
            total_fed += fed
            total_cvt += cvt
            sells_processed += count

        # Net realised under each status = gross_gain - brokerage - FED - CVT - CGT
        non_cgt_charges = total_brokerage + total_fed + total_cvt
        net_filer = total_gross_gain - non_cgt_charges - cgt_filer_total
        net_nonfiler = total_gross_gain - non_cgt_charges - cgt_nonfiler_total
        savings = cgt_nonfiler_total - cgt_filer_total

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "sells_processed": sells_processed,
            "total_gross_gain_pkr": total_gross_gain.quantize(_TWO),
            "total_brokerage_pkr": total_brokerage.quantize(_TWO),
            "total_fed_pkr": total_fed.quantize(_TWO),
            "total_cvt_pkr": total_cvt.quantize(_TWO),
            "filer": {
                "cgt_pkr": cgt_filer_total.quantize(_TWO),
                "net_realised_pkr": net_filer.quantize(_TWO),
            },
            "non_filer": {
                "cgt_pkr": cgt_nonfiler_total.quantize(_TWO),
                "net_realised_pkr": net_nonfiler.quantize(_TWO),
            },
            "filer_savings_pkr": savings.quantize(_TWO),
            "filer_savings_pct": (
                (savings / cgt_nonfiler_total * 100).quantize(_TWO)
                if cgt_nonfiler_total > 0
                else Decimal("0")
            ),
            "narrative": _narrative(savings, sells_processed),
        }

    # ── Internals ─────────────────────────────────────────────────

    async def _simulate_portfolio(
        self,
        portfolio: Portfolio,
        brackets: Sequence[TaxBracket],
        *,
        date_from: date,
        date_to: date,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, int]:
        """
        Returns (cgt_filer, cgt_nonfiler, gross_gain, brokerage, fed, cvt, sell_count).
        """
        # Pull every transaction for this portfolio (need the full history
        # to match buys against sells, even buys outside the window).
        txns = (
            (
                await self._db.execute(
                    select(Transaction)
                    .where(Transaction.portfolio_id == portfolio.id)
                    .order_by(Transaction.transaction_date, Transaction.created_at)
                )
            )
            .scalars()
            .all()
        )

        # Lot tracking per symbol
        lots_by_symbol: dict[str, list[dict[str, Any]]] = {}
        cgt_filer = Decimal("0")
        cgt_nonfiler = Decimal("0")
        gross_gain = Decimal("0")
        brokerage = Decimal("0")
        fed = Decimal("0")
        cvt = Decimal("0")
        sell_count = 0

        for t in txns:
            if t.transaction_type in ("buy", "bonus", "rights"):
                lots_by_symbol.setdefault(t.symbol, []).append(
                    {
                        "transaction_id": t.id,
                        "buy_date": t.transaction_date,
                        "quantity": t.quantity,
                        "price_per_share": t.price_per_share,
                    }
                )
            elif t.transaction_type == "sell":
                # Build BuyLots from the live tracking dict
                lots = [
                    BuyLot(
                        transaction_id=lot["transaction_id"],
                        buy_date=lot["buy_date"],
                        quantity=lot["quantity"],
                        price_per_share=lot["price_per_share"],
                    )
                    for lot in lots_by_symbol.get(t.symbol, [])
                    if lot["quantity"] > 0
                ]
                if not lots:
                    continue
                # Run match_fifo twice — different is_filer flags
                try:
                    filer_result = match_fifo(
                        lots,
                        sell_quantity=t.quantity,
                        sell_price=t.price_per_share,
                        sell_date=t.transaction_date,
                        is_filer=True,
                        brackets=brackets,
                    )
                    nonfiler_result = match_fifo(
                        lots,
                        sell_quantity=t.quantity,
                        sell_price=t.price_per_share,
                        sell_date=t.transaction_date,
                        is_filer=False,
                        brackets=brackets,
                    )
                except NoApplicableTaxRuleError:
                    continue

                # Within window: count toward simulator output
                if date_from <= t.transaction_date <= date_to:
                    cgt_filer += filer_result.total_cgt_pkr
                    cgt_nonfiler += nonfiler_result.total_cgt_pkr
                    gross_gain += filer_result.total_gross_gain_pkr  # same in both
                    brokerage += t.brokerage_pkr
                    fed += t.fed_pkr
                    cvt += t.cvt_pkr
                    sell_count += 1

                # Always update lot quantities (FIFO consumption uses same
                # match in both branches, so just walk filer's matched lots)
                remaining = t.quantity
                for lot in lots_by_symbol[t.symbol]:
                    if remaining <= 0:
                        break
                    take = min(lot["quantity"], remaining)
                    lot["quantity"] -= take
                    remaining -= take

        return cgt_filer, cgt_nonfiler, gross_gain, brokerage, fed, cvt, sell_count

    @staticmethod
    def _empty_result(date_from: date, date_to: date) -> dict[str, Any]:
        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "sells_processed": 0,
            "total_gross_gain_pkr": Decimal("0"),
            "total_brokerage_pkr": Decimal("0"),
            "total_fed_pkr": Decimal("0"),
            "total_cvt_pkr": Decimal("0"),
            "filer": {"cgt_pkr": Decimal("0"), "net_realised_pkr": Decimal("0")},
            "non_filer": {"cgt_pkr": Decimal("0"), "net_realised_pkr": Decimal("0")},
            "filer_savings_pkr": Decimal("0"),
            "filer_savings_pct": Decimal("0"),
            "narrative": "No portfolio activity to simulate yet. Log some trades first.",
        }


def _narrative(savings: Decimal, sells_processed: int) -> str:
    if sells_processed == 0:
        return "No sell transactions in the window — nothing to compare."
    if savings <= 0:
        return (
            f"Across {sells_processed} sell transactions in this window, your "
            "filer status didn't change the CGT outcome (most likely all gains "
            "fell into the 0%/lowest brackets)."
        )
    return (
        f"By being a tax filer, you would have kept an additional "
        f"PKR {float(savings):,.0f} from {sells_processed} sell transactions in "
        "this window. Filer status alone — same trades, same dates, same "
        "everything else."
    )
