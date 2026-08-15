"""Tests for Phase 2A pure modules: risk profile, TVM, allocation."""

from datetime import date
from decimal import Decimal

import pytest

from psx_api.goals.allocation import horizon_bucket, recommend
from psx_api.goals.tvm import _future_value, analyze
from psx_api.risk.profile import (
    QUESTIONS,
    InvalidAnswersError,
    archetype,
    evaluate,
    score,
)

# ── Risk profile ────────────────────────────────────────────────────────


class TestRiskScore:
    def _all_max(self) -> dict[str, str]:
        # Pick the highest-weight option for each question
        out: dict[str, str] = {}
        for q in QUESTIONS:
            best = max(q.options, key=lambda o: o.weight)
            out[q.id] = best.value
        return out

    def _all_min(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for q in QUESTIONS:
            worst = min(q.options, key=lambda o: o.weight)
            out[q.id] = worst.value
        return out

    def test_all_max_yields_aggressive(self) -> None:
        result = evaluate(self._all_max())
        assert result["archetype"] == "aggressive_trader"
        assert result["scores"] == {
            "risk_tolerance": 5,
            "time_horizon": 5,
            "knowledge": 5,
        }

    def test_all_min_yields_conservative(self) -> None:
        result = evaluate(self._all_min())
        assert result["archetype"] == "conservative_saver"

    def test_unknown_option_rejected(self) -> None:
        answers = self._all_max()
        answers["rt1"] = "nonexistent"
        with pytest.raises(InvalidAnswersError):
            score(answers)

    def test_missing_question_rejected(self) -> None:
        answers = self._all_max()
        del answers["kn1"]
        with pytest.raises(InvalidAnswersError):
            score(answers)

    def test_low_knowledge_caps_archetype(self) -> None:
        # High tolerance + horizon, but very low knowledge → cautious_beginner
        result = archetype({"risk_tolerance": 4, "time_horizon": 4, "knowledge": 1})
        assert result == "cautious_beginner"

    def test_short_horizon_caps_archetype(self) -> None:
        # Aggressive tolerance but short horizon → balanced_builder ceiling
        result = archetype({"risk_tolerance": 5, "time_horizon": 1, "knowledge": 5})
        assert result == "balanced_builder"


# ── TVM ────────────────────────────────────────────────────────────────


class TestTvm:
    def test_future_value_zero_rate(self) -> None:
        # 12 months × 1000 + 0 PV = 12000
        fv = _future_value(present_value=0, monthly_contribution=1000, months=12, annual_rate=0)
        assert fv == pytest.approx(12000)

    def test_future_value_compounds(self) -> None:
        # PV=100,000, no contribution, 10% / 12 months → ~110,471
        fv = _future_value(
            present_value=100_000, monthly_contribution=0, months=12, annual_rate=0.10
        )
        assert fv == pytest.approx(110_471, rel=1e-3)

    def test_already_funded(self) -> None:
        result = analyze(
            target_amount_pkr=Decimal("100000"),
            current_amount_pkr=Decimal("150000"),
            monthly_contribution_pkr=Decimal("0"),
            target_date=date(2030, 1, 1),
            today=date(2026, 1, 1),
        )
        assert result.rating == "already_funded"
        assert result.required_cagr is None

    def test_feasible_low_required_rate(self) -> None:
        # Need ~5% CAGR: 100k now → 121k in 4yr at 5%
        result = analyze(
            target_amount_pkr=Decimal("121550"),
            current_amount_pkr=Decimal("100000"),
            monthly_contribution_pkr=Decimal("0"),
            target_date=date(2030, 1, 1),
            today=date(2026, 1, 1),
        )
        assert result.rating == "feasible"
        assert result.required_cagr is not None
        assert 4.5 < float(result.required_cagr) < 5.5

    def test_unrealistic_returns_suggestions(self) -> None:
        # Need >>20% CAGR — 1k → 1M in 5 years
        result = analyze(
            target_amount_pkr=Decimal("1000000"),
            current_amount_pkr=Decimal("1000"),
            monthly_contribution_pkr=Decimal("1000"),
            target_date=date(2031, 1, 1),
            today=date(2026, 1, 1),
        )
        assert result.rating in ("aggressive", "unrealistic")
        if result.rating == "unrealistic":
            assert result.suggested_monthly_contribution_pkr is not None

    def test_zero_months_remaining(self) -> None:
        result = analyze(
            target_amount_pkr=Decimal("100000"),
            current_amount_pkr=Decimal("50000"),
            monthly_contribution_pkr=Decimal("0"),
            target_date=date(2026, 1, 1),
            today=date(2026, 1, 1),
        )
        assert result.rating == "unrealistic"
        assert result.months_remaining == 0


# ── Allocation ──────────────────────────────────────────────────────────


class TestAllocation:
    def test_horizon_buckets(self) -> None:
        assert horizon_bucket(12) == "short"
        assert horizon_bucket(36) == "medium"
        assert horizon_bucket(96) == "long"
        assert horizon_bucket(240) == "very_long"

    def test_aggressive_long_is_all_equity(self) -> None:
        a = recommend(archetype="aggressive_trader", months_remaining=240)
        assert a.equity_pct == 100
        assert a.tbills_pct == 0
        assert a.cash_pct == 0

    def test_conservative_short_is_all_safe(self) -> None:
        a = recommend(archetype="conservative_saver", months_remaining=12)
        assert a.equity_pct == 0
        assert a.tbills_pct + a.cash_pct == 100

    def test_unknown_archetype_falls_back_to_balanced(self) -> None:
        a = recommend(archetype="nonexistent", months_remaining=120)
        assert a.archetype == "balanced_builder"

    def test_all_buckets_sum_to_100(self) -> None:
        for arche in (
            "conservative_saver",
            "cautious_beginner",
            "balanced_builder",
            "growth_seeker",
            "aggressive_trader",
        ):
            for months in (12, 36, 96, 240):
                a = recommend(archetype=arche, months_remaining=months)
                assert a.equity_pct + a.tbills_pct + a.cash_pct == 100, (
                    f"{arche} @ {months}m doesn't sum to 100: "
                    f"{a.equity_pct}/{a.tbills_pct}/{a.cash_pct}"
                )
