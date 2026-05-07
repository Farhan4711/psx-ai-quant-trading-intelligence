"""
Tests for the adjusted-price computation algorithm.

These are pure unit tests — no database, no network.
The algorithm is the most correctness-critical code in the system:
wrong adjusted prices silently corrupt every backtest.
"""

from datetime import date
from decimal import Decimal

import pytest

from psx_ingest.adjustments import (
    CorporateEvent,
    PriceRow,
    _event_to_adjustment,
    compute_adjusted_prices,
)


# ── Helper factories ──────────────────────────────────────────────────────────

def price(d: str, close: str) -> PriceRow:
    return PriceRow(date=date.fromisoformat(d), close=Decimal(close))


def event(
    ex: str,
    action: str,
    amount: str | None = None,
    num: int | None = None,
    den: int | None = None,
) -> CorporateEvent:
    return CorporateEvent(
        ex_date=date.fromisoformat(ex),
        action_type=action,
        amount_per_share=Decimal(amount) if amount else None,
        ratio_numerator=num,
        ratio_denominator=den,
    )


# ── No-event baseline ─────────────────────────────────────────────────────────

class TestNoEvents:
    def test_adjusted_equals_close_when_no_events(self) -> None:
        prices = [price("2024-01-01", "100"), price("2024-01-02", "102")]
        result = compute_adjusted_prices(prices, [])
        for r in result:
            assert r.adjusted_close == r.close

    def test_returns_empty_for_empty_input(self) -> None:
        assert compute_adjusted_prices([], []) == []

    def test_single_price_row(self) -> None:
        result = compute_adjusted_prices([price("2024-01-01", "150")], [])
        assert result[0].adjusted_close == Decimal("150")


# ── Cash dividend adjustment ──────────────────────────────────────────────────

class TestCashDividend:
    def test_pre_ex_date_price_reduced_by_dividend(self) -> None:
        """
        Stock closes at 100 before ex-date, dividend = 5.
        Pre-ex adjusted price should be 100 - 5 = 95.
        Post-ex price is unadjusted.
        """
        prices = [
            price("2024-01-14", "100"),   # before ex-date
            price("2024-01-15", "95"),    # ex-date (price already reflects dividend)
            price("2024-01-16", "96"),    # after ex-date
        ]
        events = [event("2024-01-15", "dividend_cash", amount="5")]
        result = compute_adjusted_prices(prices, events)

        by_date = {r.date.isoformat(): r for r in result}
        # Post-ex prices are not adjusted
        assert by_date["2024-01-15"].adjusted_close == Decimal("95")
        assert by_date["2024-01-16"].adjusted_close == Decimal("96")
        # Pre-ex price reduced by dividend
        assert by_date["2024-01-14"].adjusted_close == Decimal("95")

    def test_multiple_dividends_are_cumulative(self) -> None:
        """
        Two dividends: 5 on Jan 15, 3 on Feb 15.
        A price from January should be reduced by both.
        """
        prices = [
            price("2024-01-10", "100"),
            price("2024-01-15", "95"),
            price("2024-02-15", "90"),
            price("2024-02-20", "91"),
        ]
        events = [
            event("2024-01-15", "dividend_cash", amount="5"),
            event("2024-02-15", "dividend_cash", amount="3"),
        ]
        result = compute_adjusted_prices(prices, events)
        by_date = {r.date.isoformat(): r for r in result}

        # Most recent price is unadjusted
        assert by_date["2024-02-20"].adjusted_close == Decimal("91")
        # Feb 15 price adjusted for the Feb div only? No — Feb 15 IS the ex-date.
        # Price on ex_date is NOT adjusted (the drop already happened).
        assert by_date["2024-02-15"].adjusted_close == Decimal("90")
        # Jan 15 adjusted for Feb dividend (3 subtracted)
        assert by_date["2024-01-15"].adjusted_close == Decimal("92")
        # Jan 10 adjusted for both dividends: 100 - 5 (Jan) - 3 (Feb) = 92
        assert by_date["2024-01-10"].adjusted_close == Decimal("92")


# ── Stock split / bonus adjustment ───────────────────────────────────────────

class TestSplitAndBonus:
    def test_2_for_1_split_halves_pre_split_prices(self) -> None:
        """
        2:1 split (N=1, M=1 → new price = old_price/2).
        Pre-split prices multiplied by 1/(1+1) = 0.5.
        """
        prices = [
            price("2024-01-14", "200"),   # before split
            price("2024-01-15", "100"),   # after split (already halved)
            price("2024-01-16", "101"),
        ]
        # "1 new share for every 1 held" = 2:1 split
        events = [event("2024-01-15", "split", num=1, den=1)]
        result = compute_adjusted_prices(prices, events)
        by_date = {r.date.isoformat(): r for r in result}

        assert by_date["2024-01-15"].adjusted_close == Decimal("100")
        assert by_date["2024-01-14"].adjusted_close == Decimal("100")

    def test_10_percent_bonus_shares(self) -> None:
        """
        10% bonus = 10 new shares per 100 held.
        Adjustment factor = 100 / (100 + 10) ≈ 0.9091.
        Pre-bonus price 110 → adjusted ≈ 100.
        """
        prices = [
            price("2024-01-14", "110"),
            price("2024-01-15", "100"),
            price("2024-01-16", "101"),
        ]
        events = [event("2024-01-15", "bonus", num=10, den=100)]
        result = compute_adjusted_prices(prices, events)
        by_date = {r.date.isoformat(): r for r in result}

        adj = by_date["2024-01-14"].adjusted_close
        assert adj is not None
        # Should be approximately 100 (110 × 100/110 = 100)
        assert abs(float(adj) - 100.0) < 0.01

    def test_no_adjustment_when_ratio_missing(self) -> None:
        """If bonus event has no ratio data, prices are left unchanged."""
        prices = [price("2024-01-14", "100"), price("2024-01-15", "100")]
        events = [event("2024-01-15", "bonus")]  # no num/den
        result = compute_adjusted_prices(prices, events)
        by_date = {r.date.isoformat(): r for r in result}
        assert by_date["2024-01-14"].adjusted_close == Decimal("100")


# ── AGM / stock dividend (no price effect) ──────────────────────────────────

class TestNoEffectEvents:
    def test_agm_does_not_change_prices(self) -> None:
        prices = [price("2024-01-14", "100"), price("2024-01-15", "100")]
        events = [event("2024-01-15", "agm")]
        result = compute_adjusted_prices(prices, events)
        for r in result:
            assert r.adjusted_close == r.close

    def test_dividend_stock_does_not_change_prices(self) -> None:
        prices = [price("2024-01-14", "100")]
        events = [event("2024-01-15", "dividend_stock", amount="2")]
        result = compute_adjusted_prices(prices, events)
        assert result[0].adjusted_close == Decimal("100")


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_adjusted_price_never_below_minimum(self) -> None:
        """Large dividend should not produce negative adjusted price."""
        prices = [price("2024-01-14", "5")]
        events = [event("2024-01-15", "dividend_cash", amount="100")]
        result = compute_adjusted_prices(prices, events)
        assert result[0].adjusted_close is not None
        assert result[0].adjusted_close >= Decimal("0.01")

    def test_result_sorted_ascending_by_date(self) -> None:
        prices = [
            price("2024-01-03", "103"),
            price("2024-01-01", "101"),
            price("2024-01-02", "102"),
        ]
        result = compute_adjusted_prices(prices, [])
        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_event_on_same_day_as_price(self) -> None:
        """Price on the ex-date itself should NOT be adjusted."""
        prices = [price("2024-01-15", "95")]
        events = [event("2024-01-15", "dividend_cash", amount="5")]
        result = compute_adjusted_prices(prices, events)
        # ex_date > price.date is False for same day, so no adjustment applied
        assert result[0].adjusted_close == Decimal("95")


# ── _event_to_adjustment unit tests ──────────────────────────────────────────

class TestEventToAdjustment:
    def test_cash_dividend_gives_addend(self) -> None:
        ev = event("2024-01-15", "dividend_cash", amount="5")
        mult, addend = _event_to_adjustment(ev)
        assert mult == Decimal("1")
        assert addend == Decimal("5")

    def test_split_gives_multiplier(self) -> None:
        ev = event("2024-01-15", "split", num=1, den=1)
        mult, addend = _event_to_adjustment(ev)
        assert mult == Decimal("1") / Decimal("2")
        assert addend == Decimal("0")

    def test_agm_gives_identity(self) -> None:
        ev = event("2024-01-15", "agm")
        mult, addend = _event_to_adjustment(ev)
        assert mult == Decimal("1")
        assert addend == Decimal("0")

    def test_bonus_missing_ratio_gives_identity(self) -> None:
        ev = event("2024-01-15", "bonus")
        mult, addend = _event_to_adjustment(ev)
        assert mult == Decimal("1")
        assert addend == Decimal("0")
