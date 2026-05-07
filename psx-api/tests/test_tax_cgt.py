"""Tests for the pure-Python CGT engine in psx_api.tax.cgt."""

from datetime import date
from decimal import Decimal

import pytest

from psx_api.tax.cgt import (
    BuyLot,
    CgtResult,
    InsufficientLotsError,
    NoApplicableTaxRule,
    TaxBracket,
    calculate_cgt,
    find_bracket,
    match_fifo,
)


# ── Bracket fixtures matching the seed data in migration 0006 ──────────────


@pytest.fixture
def brackets() -> list[TaxBracket]:
    pre_2024_filer = [
        (0, 365, "15.0"),
        (366, 730, "12.5"),
        (731, 1095, "10.0"),
        (1096, 1460, "7.5"),
        (1461, None, "0.0"),
    ]
    pre_2024_nonfiler = [
        (0, 365, "30.0"),
        (366, 730, "25.0"),
        (731, 1095, "20.0"),
        (1096, 1460, "15.0"),
        (1461, None, "0.0"),
    ]
    out: list[TaxBracket] = []
    for is_filer, rows in [(True, pre_2024_filer), (False, pre_2024_nonfiler)]:
        for min_d, max_d, rate in rows:
            out.append(
                TaxBracket(
                    effective_from=date(2022, 7, 1),
                    effective_to=date(2024, 6, 30),
                    is_filer=is_filer,
                    min_holding_days=min_d,
                    max_holding_days=max_d,
                    rate_pct=Decimal(rate),
                )
            )
    out.append(
        TaxBracket(
            effective_from=date(2024, 7, 1),
            effective_to=None,
            is_filer=True,
            min_holding_days=0,
            max_holding_days=None,
            rate_pct=Decimal("15.0"),
        )
    )
    out.append(
        TaxBracket(
            effective_from=date(2024, 7, 1),
            effective_to=None,
            is_filer=False,
            min_holding_days=0,
            max_holding_days=None,
            rate_pct=Decimal("45.0"),
        )
    )
    return out


# ── find_bracket ────────────────────────────────────────────────────────────


class TestFindBracket:
    def test_post_2024_filer_flat(self, brackets: list[TaxBracket]) -> None:
        b = find_bracket(
            brackets, sell_date=date(2025, 1, 15), is_filer=True, holding_period_days=10
        )
        assert b.rate_pct == Decimal("15.0")
        assert b.effective_to is None

    def test_post_2024_filer_long_hold_still_flat(self, brackets: list[TaxBracket]) -> None:
        b = find_bracket(
            brackets, sell_date=date(2025, 1, 15), is_filer=True, holding_period_days=2000
        )
        assert b.rate_pct == Decimal("15.0")

    def test_post_2024_nonfiler(self, brackets: list[TaxBracket]) -> None:
        b = find_bracket(
            brackets, sell_date=date(2025, 1, 15), is_filer=False, holding_period_days=10
        )
        assert b.rate_pct == Decimal("45.0")

    def test_pre_2024_filer_short_hold(self, brackets: list[TaxBracket]) -> None:
        b = find_bracket(
            brackets, sell_date=date(2024, 1, 15), is_filer=True, holding_period_days=100
        )
        assert b.rate_pct == Decimal("15.0")
        assert b.max_holding_days == 365

    def test_pre_2024_filer_two_to_three_years(self, brackets: list[TaxBracket]) -> None:
        b = find_bracket(
            brackets, sell_date=date(2024, 1, 15), is_filer=True, holding_period_days=900
        )
        assert b.rate_pct == Decimal("10.0")

    def test_pre_2024_filer_over_four_years_zero(self, brackets: list[TaxBracket]) -> None:
        b = find_bracket(
            brackets, sell_date=date(2024, 1, 15), is_filer=True, holding_period_days=2000
        )
        assert b.rate_pct == Decimal("0.0")

    def test_no_match_raises(self, brackets: list[TaxBracket]) -> None:
        with pytest.raises(NoApplicableTaxRule):
            find_bracket(
                brackets,
                sell_date=date(2020, 1, 1),  # before any rule's effective_from
                is_filer=True,
                holding_period_days=10,
            )

    def test_bracket_boundary_min_inclusive(self, brackets: list[TaxBracket]) -> None:
        # 366 days lands in the 366–730 bracket, not 0–365
        b = find_bracket(
            brackets, sell_date=date(2024, 1, 15), is_filer=True, holding_period_days=366
        )
        assert b.min_holding_days == 366

    def test_bracket_boundary_max_inclusive(self, brackets: list[TaxBracket]) -> None:
        # 365 days is still in 0–365
        b = find_bracket(
            brackets, sell_date=date(2024, 1, 15), is_filer=True, holding_period_days=365
        )
        assert b.max_holding_days == 365
        assert b.rate_pct == Decimal("15.0")


# ── calculate_cgt ───────────────────────────────────────────────────────────


class TestCalculateCgt:
    def test_simple_gain_filer_post_2024(self, brackets: list[TaxBracket]) -> None:
        # Buy 100 @ PKR 100, sell 100 @ PKR 150 → PKR 5000 gain → 15% = PKR 750
        cgt = calculate_cgt(
            buy_price=Decimal("100"),
            sell_price=Decimal("150"),
            quantity=Decimal("100"),
            holding_period_days=200,
            is_filer=True,
            sell_date=date(2025, 1, 15),
            brackets=brackets,
        )
        assert cgt == Decimal("750.00")

    def test_loss_yields_zero_cgt(self, brackets: list[TaxBracket]) -> None:
        cgt = calculate_cgt(
            buy_price=Decimal("100"),
            sell_price=Decimal("80"),
            quantity=Decimal("100"),
            holding_period_days=200,
            is_filer=True,
            sell_date=date(2025, 1, 15),
            brackets=brackets,
        )
        assert cgt == Decimal("0.00")

    def test_break_even_yields_zero(self, brackets: list[TaxBracket]) -> None:
        cgt = calculate_cgt(
            buy_price=Decimal("100"),
            sell_price=Decimal("100"),
            quantity=Decimal("100"),
            holding_period_days=200,
            is_filer=True,
            sell_date=date(2025, 1, 15),
            brackets=brackets,
        )
        assert cgt == Decimal("0.00")

    def test_nonfiler_post_2024_higher_rate(self, brackets: list[TaxBracket]) -> None:
        # PKR 5000 gain * 45% = PKR 2250
        cgt = calculate_cgt(
            buy_price=Decimal("100"),
            sell_price=Decimal("150"),
            quantity=Decimal("100"),
            holding_period_days=200,
            is_filer=False,
            sell_date=date(2025, 1, 15),
            brackets=brackets,
        )
        assert cgt == Decimal("2250.00")

    def test_pre_2024_long_hold_zero_rate(self, brackets: list[TaxBracket]) -> None:
        # Sold pre-Finance-Act-2024 after 5+ year hold → 0% rate
        cgt = calculate_cgt(
            buy_price=Decimal("100"),
            sell_price=Decimal("200"),
            quantity=Decimal("100"),
            holding_period_days=2000,
            is_filer=True,
            sell_date=date(2023, 12, 1),
            brackets=brackets,
        )
        assert cgt == Decimal("0.00")

    def test_pre_2024_two_year_hold_filer(self, brackets: list[TaxBracket]) -> None:
        # Sold pre-Finance-Act-2024, 2-yr hold, filer → 12.5% bracket
        # Gain = 50 * 100 = 5000 → 12.5% = 625
        cgt = calculate_cgt(
            buy_price=Decimal("100"),
            sell_price=Decimal("150"),
            quantity=Decimal("100"),
            holding_period_days=500,
            is_filer=True,
            sell_date=date(2023, 12, 1),
            brackets=brackets,
        )
        assert cgt == Decimal("625.00")

    def test_zero_quantity_raises(self, brackets: list[TaxBracket]) -> None:
        with pytest.raises(ValueError):
            calculate_cgt(
                buy_price=Decimal("100"),
                sell_price=Decimal("150"),
                quantity=Decimal("0"),
                holding_period_days=200,
                is_filer=True,
                sell_date=date(2025, 1, 15),
                brackets=brackets,
            )

    def test_fractional_quantity_quantizes_to_paisa(self, brackets: list[TaxBracket]) -> None:
        # 1.5 shares * (150 - 100) * 15% = 11.25
        cgt = calculate_cgt(
            buy_price=Decimal("100"),
            sell_price=Decimal("150"),
            quantity=Decimal("1.5"),
            holding_period_days=10,
            is_filer=True,
            sell_date=date(2025, 1, 15),
            brackets=brackets,
        )
        assert cgt == Decimal("11.25")


# ── match_fifo ──────────────────────────────────────────────────────────────


class TestMatchFifo:
    def test_single_lot_full_match(self, brackets: list[TaxBracket]) -> None:
        lots = [
            BuyLot(
                transaction_id="t1",
                buy_date=date(2024, 9, 1),
                quantity=Decimal("100"),
                price_per_share=Decimal("100"),
            )
        ]
        result = match_fifo(
            lots,
            sell_quantity=Decimal("100"),
            sell_price=Decimal("150"),
            sell_date=date(2025, 1, 15),
            is_filer=True,
            brackets=brackets,
        )
        assert isinstance(result, CgtResult)
        assert len(result.matched) == 1
        assert result.matched[0].quantity == Decimal("100")
        assert result.total_gross_gain_pkr == Decimal("5000.00")
        assert result.total_cgt_pkr == Decimal("750.00")
        assert result.weighted_avg_buy_price == Decimal("100.0000")

    def test_partial_lot_match(self, brackets: list[TaxBracket]) -> None:
        lots = [
            BuyLot(
                transaction_id="t1",
                buy_date=date(2024, 9, 1),
                quantity=Decimal("200"),
                price_per_share=Decimal("100"),
            )
        ]
        result = match_fifo(
            lots,
            sell_quantity=Decimal("50"),
            sell_price=Decimal("120"),
            sell_date=date(2025, 1, 15),
            is_filer=True,
            brackets=brackets,
        )
        assert len(result.matched) == 1
        assert result.matched[0].quantity == Decimal("50")
        # 50 * (120-100) = 1000 gain * 15% = 150
        assert result.total_cgt_pkr == Decimal("150.00")

    def test_fifo_oldest_first_across_lots(self, brackets: list[TaxBracket]) -> None:
        # Lot A: older, 50 @ 100 (held 365 days at sell)
        # Lot B: newer, 50 @ 110 (held 30 days at sell)
        # Sell 75 @ 150 → consume Lot A fully (50), then 25 from Lot B
        lots = [
            BuyLot("A", date(2024, 1, 15), Decimal("50"), Decimal("100")),
            BuyLot("B", date(2024, 12, 15), Decimal("50"), Decimal("110")),
        ]
        result = match_fifo(
            lots,
            sell_quantity=Decimal("75"),
            sell_price=Decimal("150"),
            sell_date=date(2025, 1, 14),
            is_filer=True,
            brackets=brackets,
        )
        assert len(result.matched) == 2
        assert result.matched[0].transaction_id == "A"
        assert result.matched[0].quantity == Decimal("50")
        assert result.matched[1].transaction_id == "B"
        assert result.matched[1].quantity == Decimal("25")

        # Lot A: 50 * (150-100) = 2500 → 15% = 375
        # Lot B: 25 * (150-110) = 1000 → 15% = 150
        # Total: 525
        assert result.matched[0].cgt_pkr == Decimal("375.00")
        assert result.matched[1].cgt_pkr == Decimal("150.00")
        assert result.total_cgt_pkr == Decimal("525.00")

        # Weighted avg buy: (50*100 + 25*110) / 75 = 7750/75 = 103.3333
        assert result.weighted_avg_buy_price == Decimal("103.3333")

    def test_lot_at_a_loss_has_zero_cgt(self, brackets: list[TaxBracket]) -> None:
        # One lot profits, another loses; loser contributes 0 CGT, no offset against winner
        lots = [
            BuyLot("A", date(2024, 9, 1), Decimal("50"), Decimal("100")),  # +50 each
            BuyLot("B", date(2024, 11, 1), Decimal("50"), Decimal("200")),  # -50 each
        ]
        result = match_fifo(
            lots,
            sell_quantity=Decimal("100"),
            sell_price=Decimal("150"),
            sell_date=date(2025, 1, 15),
            is_filer=True,
            brackets=brackets,
        )
        # Lot A: gain = 50 * 50 = 2500 → 15% = 375
        # Lot B: loss = 50 * -50 = -2500 → 0 CGT
        assert result.matched[0].cgt_pkr == Decimal("375.00")
        assert result.matched[1].cgt_pkr == Decimal("0.00")
        assert result.total_cgt_pkr == Decimal("375.00")
        # But total_gross_gain_pkr nets the loss: 2500 + (-2500) = 0
        assert result.total_gross_gain_pkr == Decimal("0.00")

    def test_oversell_raises(self, brackets: list[TaxBracket]) -> None:
        lots = [
            BuyLot("A", date(2024, 9, 1), Decimal("50"), Decimal("100")),
        ]
        with pytest.raises(InsufficientLotsError):
            match_fifo(
                lots,
                sell_quantity=Decimal("100"),
                sell_price=Decimal("150"),
                sell_date=date(2025, 1, 15),
                is_filer=True,
                brackets=brackets,
            )

    def test_zero_quantity_raises(self, brackets: list[TaxBracket]) -> None:
        with pytest.raises(ValueError):
            match_fifo(
                [],
                sell_quantity=Decimal("0"),
                sell_price=Decimal("150"),
                sell_date=date(2025, 1, 15),
                is_filer=True,
                brackets=brackets,
            )

    def test_same_day_buys_deterministic_by_txid(self, brackets: list[TaxBracket]) -> None:
        # Two buys on the same day; FIFO should be stable by transaction_id
        lots = [
            BuyLot("zzz", date(2024, 9, 1), Decimal("10"), Decimal("100")),
            BuyLot("aaa", date(2024, 9, 1), Decimal("10"), Decimal("200")),
        ]
        result = match_fifo(
            lots,
            sell_quantity=Decimal("10"),
            sell_price=Decimal("250"),
            sell_date=date(2025, 1, 15),
            is_filer=True,
            brackets=brackets,
        )
        # Stable secondary sort by txid → "aaa" comes first
        assert result.matched[0].transaction_id == "aaa"
        assert result.matched[0].buy_price == Decimal("200")
