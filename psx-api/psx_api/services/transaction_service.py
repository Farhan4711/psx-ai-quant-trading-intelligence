"""
Transaction creation pipeline:

  preview  →  compute charges + CGT (FIFO) without persisting
  create   →  preview, then atomically insert the row + refresh holdings_snapshot

The CGT computation pulls from the tax_rules table via TaxRuleRepository,
matches the user's open buy lots against the sell using FIFO, and writes the
computed CGT into transactions.cgt_pkr at save time so the user's broker
statement and our records stay reconcilable.

For non-sells the tax engine is bypassed (CGT = 0); buys and dividends update
holdings_snapshot accordingly. Bonus and rights issues are recorded as buys
at zero cost basis (the spec keeps qty/price separate from action_type).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.portfolios import HoldingsSnapshot, Portfolio, Transaction
from psx_api.models.securities import Security
from psx_api.schemas.portfolios import (
    MatchedLotPreview,
    TransactionCreate,
    TransactionPreview,
)
from psx_api.services.tax_rule_repository import TaxRuleRepository
from psx_api.tax.cgt import (
    BuyLot,
    InsufficientLotsError,
    NoApplicableTaxRuleError,
    match_fifo,
)

if TYPE_CHECKING:
    from psx_api.models.users import User


class TransactionError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


_ZERO = Decimal("0")
_TWO_PLACES = Decimal("0.01")


class TransactionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._tax_repo = TaxRuleRepository(db)

    # ── List ──────────────────────────────────────────────────────

    async def list_for_portfolio(
        self, portfolio: Portfolio, *, limit: int = 200
    ) -> list[Transaction]:
        result = await self._db.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio.id)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Preview ───────────────────────────────────────────────────

    async def preview(
        self, portfolio: Portfolio, body: TransactionCreate, user: User
    ) -> TransactionPreview:
        await self._validate_symbol(body.symbol)

        gross = (body.quantity * body.price_per_share).quantize(_TWO_PLACES)
        warnings: list[str] = []
        cgt = _ZERO
        matched: list[MatchedLotPreview] = []

        if body.transaction_type == "sell":
            try:
                cgt, matched = await self._compute_sell_cgt(portfolio, body, user)
            except InsufficientLotsError as exc:
                warnings.append(str(exc))
            except NoApplicableTaxRuleError as exc:
                warnings.append(f"Tax rule lookup failed: {exc}")

        total_charges = (body.brokerage_pkr + body.fed_pkr + body.cvt_pkr + cgt).quantize(
            _TWO_PLACES
        )

        if body.transaction_type == "buy":
            net = -(gross + body.brokerage_pkr + body.fed_pkr + body.cvt_pkr)
        elif body.transaction_type == "sell":
            net = gross - body.brokerage_pkr - body.fed_pkr - body.cvt_pkr - cgt
        elif body.transaction_type == "dividend":
            # `gross` here is total dividend cash received (qty=shares, price=DPS)
            net = gross - body.brokerage_pkr - body.fed_pkr - body.cvt_pkr
        else:
            # bonus / rights — no cash impact at issuance
            net = -(body.brokerage_pkr + body.fed_pkr + body.cvt_pkr)

        return TransactionPreview(
            transaction_type=body.transaction_type,
            symbol=body.symbol,
            quantity=body.quantity,
            price_per_share=body.price_per_share,
            gross_value_pkr=gross,
            brokerage_pkr=body.brokerage_pkr,
            fed_pkr=body.fed_pkr,
            cvt_pkr=body.cvt_pkr,
            cgt_pkr=cgt,
            total_charges_pkr=total_charges,
            net_cash_impact_pkr=net.quantize(_TWO_PLACES),
            matched_lots=matched,
            warnings=warnings,
        )

    # ── Create ────────────────────────────────────────────────────

    async def create(
        self, portfolio: Portfolio, body: TransactionCreate, user: User
    ) -> tuple[Transaction, TransactionPreview]:
        preview = await self.preview(portfolio, body, user)
        if preview.warnings:
            raise TransactionError("Cannot save transaction: " + "; ".join(preview.warnings))

        txn = Transaction(
            portfolio_id=portfolio.id,
            symbol=body.symbol,
            transaction_type=body.transaction_type,
            transaction_date=body.transaction_date,
            quantity=body.quantity,
            price_per_share=body.price_per_share,
            brokerage_pkr=body.brokerage_pkr,
            fed_pkr=body.fed_pkr,
            cvt_pkr=body.cvt_pkr,
            cgt_pkr=preview.cgt_pkr,
            notes=body.notes,
        )
        self._db.add(txn)
        await self._db.flush()
        await self._db.refresh(txn)

        await self._refresh_holdings_snapshot(portfolio, body.symbol)

        return txn, preview

    # ── Internals ─────────────────────────────────────────────────

    async def _validate_symbol(self, symbol: str) -> None:
        result = await self._db.execute(select(Security).where(Security.symbol == symbol))
        if result.scalar_one_or_none() is None:
            raise TransactionError(f"Unknown symbol '{symbol}'.", status_code=404)

    async def _compute_sell_cgt(
        self, portfolio: Portfolio, body: TransactionCreate, user: User
    ) -> tuple[Decimal, list[MatchedLotPreview]]:
        # Pull all open lots for this symbol — order by buy date so FIFO is deterministic.
        # "Open" = sum of buy/bonus/rights minus prior sells. We naively pass all buys to
        # match_fifo; the caller is responsible for tracking consumed quantity per lot
        # but for preview we approximate by reducing each lot by prior sell quantity FIFO.
        buys_result = await self._db.execute(
            select(Transaction)
            .where(
                Transaction.portfolio_id == portfolio.id,
                Transaction.symbol == body.symbol,
                Transaction.transaction_type.in_(("buy", "bonus", "rights")),
            )
            .order_by(Transaction.transaction_date, Transaction.created_at)
        )
        buys = list(buys_result.scalars().all())

        sells_result = await self._db.execute(
            select(Transaction)
            .where(
                Transaction.portfolio_id == portfolio.id,
                Transaction.symbol == body.symbol,
                Transaction.transaction_type == "sell",
            )
            .order_by(Transaction.transaction_date, Transaction.created_at)
        )
        prior_sells = list(sells_result.scalars().all())

        # Reduce open lot quantities by prior sells (FIFO consumption).
        open_qty: dict[str, Decimal] = {b.id: b.quantity for b in buys}
        sell_remaining = sum((s.quantity for s in prior_sells), Decimal("0"))
        for b in buys:  # already FIFO-sorted by query
            if sell_remaining <= 0:
                break
            take = min(open_qty[b.id], sell_remaining)
            open_qty[b.id] -= take
            sell_remaining -= take

        lots = [
            BuyLot(
                transaction_id=b.id,
                buy_date=b.transaction_date,
                quantity=open_qty[b.id],
                price_per_share=b.price_per_share,
            )
            for b in buys
            if open_qty[b.id] > 0
        ]

        brackets = await self._tax_repo.load_cgt_brackets()
        result = match_fifo(
            lots,
            sell_quantity=body.quantity,
            sell_price=body.price_per_share,
            sell_date=body.transaction_date,
            is_filer=user.is_filer,
            brackets=brackets,
        )

        previews = [
            MatchedLotPreview(
                transaction_id=m.transaction_id,
                buy_date=m.buy_date,
                quantity=m.quantity,
                buy_price=m.buy_price,
                holding_period_days=m.holding_period_days,
                gross_gain_pkr=m.gross_gain_pkr,
                cgt_rate_pct=m.cgt_rate_pct,
                cgt_pkr=m.cgt_pkr,
            )
            for m in result.matched
        ]
        return result.total_cgt_pkr, previews

    async def _refresh_holdings_snapshot(self, portfolio: Portfolio, symbol: str) -> None:
        """
        Recompute holdings_snapshot for (portfolio, symbol) from the full
        transaction history. O(n) per symbol — fine for retail volumes; if
        this becomes a hot path we'll switch to incremental updates.
        """
        txns_result = await self._db.execute(
            select(Transaction)
            .where(
                Transaction.portfolio_id == portfolio.id,
                Transaction.symbol == symbol,
            )
            .order_by(Transaction.transaction_date, Transaction.created_at)
        )
        txns = list(txns_result.scalars().all())

        # Lot-level FIFO state for accurate avg cost across partial sells
        lots: list[list[Decimal]] = []  # [[qty, price], ...]
        realized_pnl = Decimal("0")
        dividends = Decimal("0")
        total_invested = Decimal("0")

        for t in txns:
            if t.transaction_type in ("buy", "bonus", "rights"):
                lots.append([t.quantity, t.price_per_share])
                total_invested += t.quantity * t.price_per_share
            elif t.transaction_type == "sell":
                remaining = t.quantity
                while remaining > 0 and lots:
                    take = min(lots[0][0], remaining)
                    realized_pnl += (t.price_per_share - lots[0][1]) * take
                    lots[0][0] -= take
                    remaining -= take
                    if lots[0][0] == 0:
                        lots.pop(0)
            elif t.transaction_type == "dividend":
                dividends += t.quantity * t.price_per_share

        open_qty = sum((lot[0] for lot in lots), Decimal("0"))
        weighted_cost = sum((lot[0] * lot[1] for lot in lots), Decimal("0"))
        avg_cost = (weighted_cost / open_qty) if open_qty > 0 else Decimal("0")

        # Upsert snapshot row
        existing = (
            await self._db.execute(
                select(HoldingsSnapshot).where(
                    HoldingsSnapshot.portfolio_id == portfolio.id,
                    HoldingsSnapshot.symbol == symbol,
                )
            )
        ).scalar_one_or_none()

        if open_qty == 0 and dividends == 0 and realized_pnl == 0:
            if existing:
                await self._db.delete(existing)
            return

        if existing is None:
            existing = HoldingsSnapshot(
                portfolio_id=portfolio.id,
                symbol=symbol,
                quantity=open_qty,
                avg_cost_pkr=avg_cost.quantize(Decimal("0.0001")),
                total_invested_pkr=total_invested.quantize(_TWO_PLACES),
                realized_pnl_pkr=realized_pnl.quantize(_TWO_PLACES),
                total_dividends_received_pkr=dividends.quantize(_TWO_PLACES),
            )
            self._db.add(existing)
        else:
            existing.quantity = open_qty
            existing.avg_cost_pkr = avg_cost.quantize(Decimal("0.0001"))
            existing.total_invested_pkr = total_invested.quantize(_TWO_PLACES)
            existing.realized_pnl_pkr = realized_pnl.quantize(_TWO_PLACES)
            existing.total_dividends_received_pkr = dividends.quantize(_TWO_PLACES)

        await self._db.flush()
