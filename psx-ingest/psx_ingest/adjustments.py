# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
Adjusted-price computation for split-and-dividend adjustment.

PSX-specific corporate events that affect historical prices:
  - Stock splits:       multiply all pre-split prices by (1 / split_ratio)
  - Bonus shares:       same treatment as splits — dilutes share price
  - Rights issues:      treated as partial splits + new-money injection
  - Cash dividends:     subtract dividend from all pre-ex-date prices (additive method)

We use the Pandas-compatible "backward adjustment" convention:
  - The MOST RECENT close price is always equal to the raw close price
  - ALL older prices are adjusted downward to reflect what the price
    WOULD HAVE BEEN if the corporate event had not occurred

Why this matters:
  A stock trading at 200 that does a 2:1 split will open at ~100 the next day.
  Without adjustment, any percentage-return calculation that crosses the split
  date will show a spurious -50% loss. Adjusted prices eliminate this artifact.

References:
  - Standard CRSP adjustment methodology
  - PSX circular: Calculation of Adjusted Closing Price (circular no. CSD/D-2/2020-...)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class CorporateEvent:
    """Lightweight representation of a single corporate event."""
    ex_date: date
    action_type: str          # matches models.corporate_actions VALID_ACTION_TYPES
    amount_per_share: Decimal | None = None   # cash dividend per share (PKR)
    ratio_numerator: int | None = None        # bonus/split: N new shares
    ratio_denominator: int | None = None      # bonus/split: for every M held


@dataclass
class PriceRow:
    date: date
    close: Decimal
    adjusted_close: Decimal | None = None


_FOUR = Decimal("0.0001")   # rounding scale


def compute_adjusted_prices(
    prices: list[PriceRow],
    events: list[CorporateEvent],
) -> list[PriceRow]:
    """
    Computes split-and-dividend adjusted closing prices using backward adjustment.

    Args:
        prices: OHLCV rows sorted by date ASCENDING, each with a raw close.
        events: Corporate events sorted by ex_date ASCENDING.

    Returns:
        Same list of PriceRow objects with adjusted_close populated.
        The most recent row's adjusted_close == its close (no adjustment needed).

    Algorithm (backward pass):
        1. Start from the newest price. adjusted_close = close.
        2. Walk backwards. When we cross an ex_date:
           - For splits/bonus: multiply all older adjusted prices by the
             pre-event factor = denominator / (denominator + numerator)
           - For cash dividends: subtract amount_per_share from all older prices
        3. Clamp to minimum of 0.01 to avoid negative adjusted prices.
    """
    if not prices:
        return prices

    # Sort ascending by date (newest last)
    sorted_prices = sorted(prices, key=lambda r: r.date)

    # Work out cumulative adjustment factors by iterating events newest-first.
    # We apply adjustments cumulatively as we walk backwards through time.
    sorted_events = sorted(events, key=lambda e: e.ex_date, reverse=True)

    # Build list of (ex_date, multiplier, addend) tuples newest-first
    adjustments: list[tuple[date, Decimal, Decimal]] = []
    for event in sorted_events:
        mult, addend = _event_to_adjustment(event)
        adjustments.append((event.ex_date, mult, addend))

    # Backward pass
    cumulative_mult = Decimal("1")
    cumulative_add = Decimal("0")
    adj_idx = 0   # pointer into adjustments list (newest-first)

    result: list[PriceRow] = []
    for price_row in reversed(sorted_prices):
        # Apply any events whose ex_date > current price date
        while adj_idx < len(adjustments):
            ex_date, mult, addend = adjustments[adj_idx]
            if ex_date > price_row.date:
                # This event happened AFTER current date → adjust cumulative factors
                cumulative_mult = cumulative_mult * mult
                cumulative_add = cumulative_add * mult + addend
                adj_idx += 1
            else:
                break

        adj_close = price_row.close * cumulative_mult - cumulative_add
        # Clamp to avoid negative or zero adjusted prices
        adj_close = max(adj_close, Decimal("0.01"))
        adj_close = adj_close.quantize(_FOUR, rounding=ROUND_HALF_UP)

        result.append(PriceRow(
            date=price_row.date,
            close=price_row.close,
            adjusted_close=adj_close,
        ))

    # Re-sort ascending before returning
    result.reverse()
    return result


def _event_to_adjustment(event: CorporateEvent) -> tuple[Decimal, Decimal]:
    """
    Returns (multiplier, addend) representing the backward adjustment for one event.

    For the pre-ex-date price P, the adjusted price is:
        adjusted_P = P * multiplier - addend

    Splits / bonus shares:
        After N new shares per M held, price decreases by factor M/(M+N).
        Backward adjustment multiplies old prices by M/(M+N).
        multiplier = M / (M + N),  addend = 0

    Cash dividends:
        Price drops by the dividend amount on ex-date.
        Backward adjustment subtracts dividend from old prices.
        multiplier = 1,  addend = amount_per_share

    Rights issues:
        Treated as partial split: ratio-only adjustment (ignoring new-money
        injection as a simplification for EOD price purposes).
        multiplier = M / (M + N),  addend = 0
    """
    action = event.action_type

    if action in ("split", "bonus", "rights"):
        num = event.ratio_numerator
        den = event.ratio_denominator
        if num and den and den > 0:
            multiplier = Decimal(den) / Decimal(den + num)
            return multiplier, Decimal("0")
        # Fallback: no ratio data — leave price unchanged
        return Decimal("1"), Decimal("0")

    if action in ("dividend_cash",):
        amt = event.amount_per_share or Decimal("0")
        return Decimal("1"), amt

    # dividend_stock / agm — no price adjustment needed
    return Decimal("1"), Decimal("0")
