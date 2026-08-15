"""Tests for Phase 4 pure modules: buckets, strategy parser, purification, lessons."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from psx_api.backtest.engine import Bar
from psx_api.benchmark.buckets import (
    age_bucket,
    archetype_bucket,
    bucket_label,
    percentile_rank,
    size_bucket,
)
from psx_api.learning.curriculum import (
    CURRICULUM,
    grade_attempt,
    quiz_to_jsonable,
)
from psx_api.purification.calculator import (
    DividendRecord,
    compute_report,
)
from psx_api.strategy_builder.parse import (
    InvalidStrategyError,
    build_strategy,
    validate,
)

# ── Buckets ─────────────────────────────────────────────────────────────


class TestBuckets:
    def test_age_buckets(self) -> None:
        today = date(2026, 5, 8)
        assert age_bucket(date(2005, 1, 1), today=today) == "18-24"
        assert age_bucket(date(2000, 1, 1), today=today) == "25-34"
        assert age_bucket(date(1985, 1, 1), today=today) == "35-44"
        assert age_bucket(date(1975, 1, 1), today=today) == "45-54"
        assert age_bucket(date(1960, 1, 1), today=today) == "55+"
        assert age_bucket(None) == "unknown"

    def test_size_buckets(self) -> None:
        assert size_bucket(50_000) == "<100K"
        assert size_bucket(250_000) == "100K-500K"
        assert size_bucket(1_500_000) == "500K-2M"
        assert size_bucket(5_000_000) == "2M-10M"
        assert size_bucket(50_000_000) == "10M+"
        assert size_bucket(None) == "unknown"

    def test_label_pretty(self) -> None:
        label = bucket_label("aggressive_trader", "25-34", "100K-500K")
        assert "Aggressive Trader" in label
        assert "25-34" in label

    def test_archetype_unknown(self) -> None:
        assert archetype_bucket(None) == "unknown"
        assert archetype_bucket("balanced_builder") == "balanced_builder"

    def test_percentile_rank(self) -> None:
        dist = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert percentile_rank(35, dist) == 60  # 3 of 5 below
        assert percentile_rank(5, dist) == 0
        assert percentile_rank(99, dist) == 100
        assert percentile_rank(35, []) == 50


# ── Purification ────────────────────────────────────────────────────────


class TestPurification:
    def test_basic_5pct(self) -> None:
        divs = [
            DividendRecord("ENGRO", date(2025, 6, 1), Decimal("1000")),
            DividendRecord("LUCK", date(2025, 9, 1), Decimal("500")),
        ]
        report = compute_report(divs, fiscal_year=2025)
        assert report.total_dividends_pkr == Decimal("1500.00")
        assert report.total_purification_pkr == Decimal("75.00")  # 5% of 1500
        assert len(report.lines) == 2

    def test_filters_to_fiscal_year(self) -> None:
        divs = [
            DividendRecord("ENGRO", date(2024, 6, 1), Decimal("1000")),  # different year
            DividendRecord("LUCK", date(2025, 6, 1), Decimal("500")),
        ]
        report = compute_report(divs, fiscal_year=2025)
        assert report.total_dividends_pkr == Decimal("500.00")
        assert len(report.lines) == 1
        assert report.lines[0].symbol == "LUCK"

    def test_custom_pct(self) -> None:
        divs = [DividendRecord("ENGRO", date(2025, 6, 1), Decimal("2000"))]
        report = compute_report(divs, fiscal_year=2025, purification_pct=Decimal("3"))
        assert report.total_purification_pkr == Decimal("60.00")

    def test_groups_same_symbol(self) -> None:
        divs = [
            DividendRecord("ENGRO", date(2025, 3, 1), Decimal("100")),
            DividendRecord("ENGRO", date(2025, 9, 1), Decimal("200")),
        ]
        report = compute_report(divs, fiscal_year=2025)
        assert len(report.lines) == 1
        assert report.lines[0].dividends_pkr == Decimal("300.00")

    def test_empty_dividends(self) -> None:
        report = compute_report([], fiscal_year=2025)
        assert report.total_dividends_pkr == Decimal("0.00")
        assert report.lines == []


# ── Strategy parser ─────────────────────────────────────────────────────


class TestStrategyParser:
    def test_valid_simple_rsi_oversold(self) -> None:
        rules = {
            "entry": {
                "operator": "<",
                "left": {"kind": "indicator", "name": "rsi", "period": 14},
                "right": {"kind": "constant", "value": 30},
            },
            "exit": {
                "operator": ">",
                "left": {"kind": "indicator", "name": "rsi", "period": 14},
                "right": {"kind": "constant", "value": 70},
            },
        }
        validate(rules)  # no raise
        strategy = build_strategy(rules)
        assert callable(strategy)

    def test_missing_entry_raises(self) -> None:
        with pytest.raises(InvalidStrategyError):
            validate({})

    def test_unknown_indicator_raises(self) -> None:
        rules = {
            "entry": {
                "operator": "<",
                "left": {"kind": "indicator", "name": "nonexistent"},
                "right": {"kind": "constant", "value": 30},
            }
        }
        with pytest.raises(InvalidStrategyError):
            validate(rules)

    def test_unknown_operator_raises(self) -> None:
        rules = {
            "entry": {
                "operator": "!?",
                "left": {"kind": "constant", "value": 1},
                "right": {"kind": "constant", "value": 2},
            }
        }
        with pytest.raises(InvalidStrategyError):
            validate(rules)

    def test_holding_days_gt_only_in_exit(self) -> None:
        rules = {
            "entry": {
                "operator": "<",
                "left": {"kind": "indicator", "name": "rsi", "period": 14},
                "right": {"kind": "constant", "value": 30},
            },
            "exit": {
                "any_of": [
                    {
                        "operator": ">",
                        "left": {"kind": "indicator", "name": "rsi", "period": 14},
                        "right": {"kind": "constant", "value": 70},
                    },
                    {"kind": "holding_days_gt", "value": 10},
                ]
            },
        }
        validate(rules)
        strategy = build_strategy(rules)

        # Synthesize bars where RSI never crosses 30 — strategy should stay flat
        start = date(2024, 1, 1)
        bars = [
            Bar(
                date=start + timedelta(days=i),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                adjusted_close=100.0,
                volume=1000.0,
            )
            for i in range(50)
        ]
        decisions = [strategy(bars, i) for i in range(20, 50)]
        # Each decision is either int or (int, str); extract the int
        targets = [d if isinstance(d, int) else d[0] for d in decisions]
        assert all(t == 0 for t in targets)


# ── Lessons / quiz grader ───────────────────────────────────────────────


class TestLessons:
    def test_curriculum_size(self) -> None:
        assert len(CURRICULUM) == 10

    def test_each_lesson_has_quiz(self) -> None:
        for lesson in CURRICULUM:
            assert len(lesson.quiz) >= 3
            for q in lesson.quiz:
                assert any(
                    o.correct for o in q.options
                ), f"Question '{q.question}' has no correct option"

    def test_each_lesson_has_unique_slug(self) -> None:
        slugs = [lesson.slug for lesson in CURRICULUM]
        assert len(slugs) == len(set(slugs))

    def test_grade_perfect_score(self) -> None:
        lesson = CURRICULUM[0]
        quiz_json = quiz_to_jsonable(lesson.quiz)
        # Find correct index for each question
        correct_answers = []
        for q in quiz_json:
            for i, o in enumerate(q["options"]):
                if o.get("correct"):
                    correct_answers.append(i)
                    break
        assert grade_attempt(quiz_json, correct_answers) == 100

    def test_grade_zero_with_all_wrong(self) -> None:
        lesson = CURRICULUM[0]
        quiz_json = quiz_to_jsonable(lesson.quiz)
        wrong = []
        for q in quiz_json:
            for i, o in enumerate(q["options"]):
                if not o.get("correct"):
                    wrong.append(i)
                    break
        assert grade_attempt(quiz_json, wrong) == 0

    def test_grade_partial(self) -> None:
        lesson = CURRICULUM[0]
        quiz_json = quiz_to_jsonable(lesson.quiz)
        # Mix: first correct, rest wrong
        answers = []
        for i, q in enumerate(quiz_json):
            for j, o in enumerate(q["options"]):
                if (i == 0) == bool(o.get("correct")):
                    answers.append(j)
                    break
        score = grade_attempt(quiz_json, answers)
        assert 0 < score < 100

    def test_grade_short_attempt_zero(self) -> None:
        lesson = CURRICULUM[0]
        quiz_json = quiz_to_jsonable(lesson.quiz)
        assert grade_attempt(quiz_json, [0]) == 0  # too few answers
