"""
Dividend purification calculator (Phase 4 Step 65).

Per Islamic finance convention used by major Pakistani Shariah funds
(Meezan Asset Management, NIT-Islamic, Al-Meezan): a small fraction of
cash dividends from KMI-compliant stocks should be donated as
"purification" because even compliant companies derive a sliver of
revenue from non-permissible sources (interest income on deposits,
incidental ancillary services).

Phase 4 v1: 5% flat rate, configurable per user. The user can adjust
the percentage and mark each annual report row as donated.

Pure functions; the service layer reads `transactions` and writes
`purification_records`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

_TWO = Decimal("0.01")
DEFAULT_PURIFICATION_PCT = Decimal("5.0")


@dataclass(frozen=True)
class DividendRecord:
    """One dividend transaction within the year for a KMI-compliant symbol."""

    symbol: str
    transaction_date: date
    amount_pkr: Decimal


@dataclass(frozen=True)
class PurificationLine:
    symbol: str
    dividends_pkr: Decimal
    purification_pct: Decimal
    purification_amount_pkr: Decimal


@dataclass(frozen=True)
class PurificationReport:
    fiscal_year: int
    total_dividends_pkr: Decimal
    total_purification_pkr: Decimal
    lines: list[PurificationLine]
    purification_pct: Decimal


def compute_report(
    dividends: list[DividendRecord],
    *,
    fiscal_year: int,
    purification_pct: Decimal | None = None,
) -> PurificationReport:
    """
    Group dividends by symbol, apply the purification rate, return the
    annual report. Only call with dividends from KMI-compliant symbols
    (the service layer filters upstream).
    """
    pct = purification_pct if purification_pct is not None else DEFAULT_PURIFICATION_PCT
    multiplier = pct / Decimal("100")

    by_symbol: dict[str, Decimal] = {}
    for div in dividends:
        if div.transaction_date.year != fiscal_year:
            continue
        by_symbol[div.symbol] = by_symbol.get(div.symbol, Decimal("0")) + div.amount_pkr

    lines = [
        PurificationLine(
            symbol=symbol,
            dividends_pkr=total.quantize(_TWO),
            purification_pct=pct,
            purification_amount_pkr=(total * multiplier).quantize(_TWO),
        )
        for symbol, total in sorted(by_symbol.items())
    ]
    total_div = sum((line.dividends_pkr for line in lines), Decimal("0"))
    total_pur = sum((line.purification_amount_pkr for line in lines), Decimal("0"))

    return PurificationReport(
        fiscal_year=fiscal_year,
        total_dividends_pkr=total_div.quantize(_TWO),
        total_purification_pkr=total_pur.quantize(_TWO),
        lines=lines,
        purification_pct=pct,
    )
