"""
Pure-Python tax engine for Pakistan CGT on listed securities.

Two responsibilities:

1. `calculate_cgt()` — given a single matched buy/sell pair, return the CGT in
   PKR using the rate in effect on `sell_date`. Pure function, no DB access.
   The caller passes in the bracket list it loaded from the `tax_rules` table.

2. `match_fifo()` — match a sell against accumulated buy lots using FIFO
   (SECP convention), returning matched lots with per-lot gain and CGT.
   Optional `lot_strategy` hook reserved for future LIFO / specific-lot.

Design notes:

- Decimal throughout. Never floats.
- Gain is `(sell_price - buy_price) * quantity - sell_brokerage_share`.
  We keep brokerage out of the CGT base for now (tax authorities differ on
  whether brokerage reduces the gain; SECP treats gross gain). The portfolio
  P&L view subtracts brokerage separately.
- A loss yields zero CGT (SECP allows offsetting against same-year gains in
  the user's annual return — that's a reporting concern, not transaction-time).
- Bracket lookup is exact match by date range, filer status, and holding
  bucket. If no bracket matches, raises `NoApplicableTaxRuleError`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

# ── Errors ──────────────────────────────────────────────────────────────


class NoApplicableTaxRuleError(Exception):
    """Raised when no tax_rules row matches the given (date, filer, holding)."""


class InsufficientLotsError(Exception):
    """Raised when a sell quantity exceeds the accumulated buy lots."""


# ── Data types ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TaxBracket:
    """In-memory representation of one row of the tax_rules table."""

    effective_from: date
    effective_to: date | None
    is_filer: bool
    min_holding_days: int
    max_holding_days: int | None  # None = unbounded
    rate_pct: Decimal


@dataclass(frozen=True)
class BuyLot:
    """A single accumulated long position from a buy transaction."""

    transaction_id: str
    buy_date: date
    quantity: Decimal
    price_per_share: Decimal


@dataclass(frozen=True)
class MatchedLot:
    """Result of matching part or all of a buy lot against a sell."""

    transaction_id: str
    buy_date: date
    sell_date: date
    quantity: Decimal
    buy_price: Decimal
    sell_price: Decimal
    holding_period_days: int
    gross_gain_pkr: Decimal
    cgt_rate_pct: Decimal
    cgt_pkr: Decimal


@dataclass(frozen=True)
class CgtResult:
    """Aggregate result from matching one sell against multiple buy lots."""

    matched: tuple[MatchedLot, ...]
    total_gross_gain_pkr: Decimal
    total_cgt_pkr: Decimal
    weighted_avg_buy_price: Decimal


# ── Internals ───────────────────────────────────────────────────────────


_TWO_PLACES = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _bracket_matches(
    bracket: TaxBracket, sell_date: date, is_filer: bool, holding_days: int
) -> bool:
    if bracket.is_filer != is_filer:
        return False
    if sell_date < bracket.effective_from:
        return False
    if bracket.effective_to is not None and sell_date > bracket.effective_to:
        return False
    if holding_days < bracket.min_holding_days:
        return False
    if bracket.max_holding_days is not None and holding_days > bracket.max_holding_days:
        return False
    return True


def find_bracket(
    brackets: Sequence[TaxBracket],
    *,
    sell_date: date,
    is_filer: bool,
    holding_period_days: int,
) -> TaxBracket:
    """
    Return the unique bracket applying to (sell_date, is_filer, holding_days).
    Raises NoApplicableTaxRuleError if no bracket matches.

    If multiple brackets match (data error in tax_rules), the most specific —
    narrowest holding range, narrowest date range — wins.
    """
    candidates = [
        b for b in brackets if _bracket_matches(b, sell_date, is_filer, holding_period_days)
    ]
    if not candidates:
        raise NoApplicableTaxRuleError(
            f"No CGT bracket for sell_date={sell_date} is_filer={is_filer} "
            f"holding_days={holding_period_days}"
        )

    # Most-specific wins: narrowest holding range, then narrowest date range.
    def _specificity(b: TaxBracket) -> tuple[int, int]:
        holding_span = (
            (b.max_holding_days - b.min_holding_days) if b.max_holding_days is not None else 10**9
        )
        date_span = (
            (b.effective_to - b.effective_from).days if b.effective_to is not None else 10**9
        )
        return (holding_span, date_span)

    candidates.sort(key=_specificity)
    return candidates[0]


# ── Public API ──────────────────────────────────────────────────────────


def calculate_cgt(
    *,
    buy_price: Decimal,
    sell_price: Decimal,
    quantity: Decimal,
    holding_period_days: int,
    is_filer: bool,
    sell_date: date,
    brackets: Sequence[TaxBracket],
) -> Decimal:
    """
    Returns CGT owed in PKR for the given matched buy/sell pair.

    A loss returns Decimal('0') — losses are reported separately and offset in
    the user's annual return. Quantized to 2 decimal places (paisa).
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    gross_gain = (sell_price - buy_price) * quantity
    if gross_gain <= 0:
        return Decimal("0.00")

    bracket = find_bracket(
        brackets,
        sell_date=sell_date,
        is_filer=is_filer,
        holding_period_days=holding_period_days,
    )
    cgt = gross_gain * bracket.rate_pct / Decimal("100")
    return _quantize(cgt)


def match_fifo(
    lots: Sequence[BuyLot],
    *,
    sell_quantity: Decimal,
    sell_price: Decimal,
    sell_date: date,
    is_filer: bool,
    brackets: Sequence[TaxBracket],
) -> CgtResult:
    """
    Match a sell against accumulated buy lots using FIFO (oldest-first) and
    return per-lot CGT plus aggregate totals.

    `lots` must be the open lots remaining for the symbol; the caller is
    responsible for tracking and removing matched quantities afterwards.
    """
    if sell_quantity <= 0:
        raise ValueError("sell_quantity must be positive")

    # FIFO: oldest buy first. Stable secondary sort by transaction_id keeps
    # the result deterministic for same-day buys.
    sorted_lots = sorted(lots, key=lambda lo: (lo.buy_date, lo.transaction_id))

    remaining = sell_quantity
    matched: list[MatchedLot] = []
    total_qty_for_avg = Decimal("0")
    weighted_cost = Decimal("0")

    for lot in sorted_lots:
        if remaining <= 0:
            break
        if lot.quantity <= 0:
            continue

        take = min(lot.quantity, remaining)
        if take <= 0:
            continue

        holding_days = (sell_date - lot.buy_date).days
        gross_gain = (sell_price - lot.price_per_share) * take

        if gross_gain > 0:
            bracket = find_bracket(
                brackets,
                sell_date=sell_date,
                is_filer=is_filer,
                holding_period_days=holding_days,
            )
            cgt = _quantize(gross_gain * bracket.rate_pct / Decimal("100"))
            rate = bracket.rate_pct
        else:
            cgt = Decimal("0.00")
            rate = Decimal("0")

        matched.append(
            MatchedLot(
                transaction_id=lot.transaction_id,
                buy_date=lot.buy_date,
                sell_date=sell_date,
                quantity=take,
                buy_price=lot.price_per_share,
                sell_price=sell_price,
                holding_period_days=holding_days,
                gross_gain_pkr=_quantize(gross_gain),
                cgt_rate_pct=rate,
                cgt_pkr=cgt,
            )
        )
        weighted_cost += lot.price_per_share * take
        total_qty_for_avg += take
        remaining -= take

    if remaining > 0:
        raise InsufficientLotsError(
            f"Sell quantity {sell_quantity} exceeds open lots; short by {remaining}"
        )

    total_gross = sum((m.gross_gain_pkr for m in matched), Decimal("0"))
    total_cgt = sum((m.cgt_pkr for m in matched), Decimal("0"))
    avg_buy = (
        (weighted_cost / total_qty_for_avg).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if total_qty_for_avg > 0
        else Decimal("0")
    )

    return CgtResult(
        matched=tuple(matched),
        total_gross_gain_pkr=_quantize(total_gross),
        total_cgt_pkr=_quantize(total_cgt),
        weighted_avg_buy_price=avg_buy,
    )
