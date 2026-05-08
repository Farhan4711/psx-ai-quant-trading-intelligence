"""Tests for Phase 3 pure modules: news extract/sentiment/pulse, alerts pump/dump."""

from datetime import date

import pytest

from psx_api.alerts.pump_dump import (
    AnomalyFeatures,
    DailyBar,
    anomaly_score,
    detect_rule,
    escalate_severity,
    features_from,
)
from psx_api.news.extract import (
    aliases_from_securities,
    build_alias_index,
    extract_mentions,
)
from psx_api.news.pulse import PulseInput, compute_pulse
from psx_api.news.sentiment import score_lexicon


# ── Entity extraction ──────────────────────────────────────────────────


class TestEntityExtraction:
    def test_finds_ticker_mentions(self) -> None:
        idx = build_alias_index([("ENGRO", "ENGRO"), ("LUCK", "LUCK")])
        out = extract_mentions("Today ENGRO and LUCK both rallied.", idx)
        assert out == {"ENGRO": 1, "LUCK": 1}

    def test_word_boundaries_dont_partial_match(self) -> None:
        idx = build_alias_index([("BANK", "BANK")])
        out = extract_mentions("BANKER reported earnings", idx)
        assert "BANK" not in out

    def test_long_aliases_take_precedence(self) -> None:
        idx = build_alias_index(
            [("ENGRO", "Engro"), ("EFERT", "Engro Fertilizers")]
        )
        out = extract_mentions("Engro Fertilizers and Engro Corp", idx)
        # "Engro Fertilizers" matches once, "Engro" matches once standalone
        assert out.get("EFERT") == 1
        assert out.get("ENGRO") == 1

    def test_aliases_from_securities_strips_legal_suffixes(self) -> None:
        rows = aliases_from_securities([("ENGRO", "Engro Corporation Limited")])
        aliases = {alias for _, alias in rows}
        assert "ENGRO" in aliases
        assert "Engro Corporation Limited" in aliases
        assert "Engro Corporation" in aliases

    def test_case_insensitive_matching(self) -> None:
        idx = build_alias_index([("ENGRO", "engro")])
        out = extract_mentions("ENGRO crashed today.", idx)
        assert out["ENGRO"] == 1


# ── Sentiment ──────────────────────────────────────────────────────────


class TestSentiment:
    def test_strongly_positive(self) -> None:
        result = score_lexicon(
            "Strong profits and record growth at Engro; dividend boosted, outperform peers."
        )
        assert result.polarity > 0.5
        assert result.event_type in ("earnings", "general")

    def test_strongly_negative(self) -> None:
        result = score_lexicon(
            "Lawsuit and fraud investigation: shares plunged after the scandal."
        )
        assert result.polarity < -0.5
        assert result.event_type == "scandal"

    def test_negation_flips_polarity(self) -> None:
        # Without negation: positive
        plain = score_lexicon("Strong growth and record profits.")
        # With negation: should flip to negative or at least drop materially
        negated = score_lexicon("No growth and not profitable.")
        assert plain.polarity > 0
        assert negated.polarity < plain.polarity

    def test_neutral(self) -> None:
        result = score_lexicon("The board met to discuss the upcoming AGM.")
        assert -0.3 <= result.polarity <= 0.3

    def test_event_type_macro(self) -> None:
        result = score_lexicon("KIBOR rose after the SBP policy rate hike.")
        assert result.event_type in ("macro", "regulatory")

    def test_empty_text(self) -> None:
        result = score_lexicon("")
        assert result.polarity == 0.0


# ── News pulse ─────────────────────────────────────────────────────────


class TestPulse:
    def test_empty_returns_zero(self) -> None:
        score = compute_pulse([], today=date(2026, 5, 8))
        assert score.score == 0.0
        assert score.article_count == 0

    def test_strong_positive_recent_articles(self) -> None:
        items = [PulseInput(polarity=1.0, published_on=date(2026, 5, 8))] * 10
        score = compute_pulse(items, today=date(2026, 5, 8))
        assert score.score > 80

    def test_strong_negative(self) -> None:
        items = [PulseInput(polarity=-1.0, published_on=date(2026, 5, 8))] * 10
        score = compute_pulse(items, today=date(2026, 5, 8))
        assert score.score < -80

    def test_old_articles_decay(self) -> None:
        recent = compute_pulse(
            [PulseInput(polarity=1.0, published_on=date(2026, 5, 8))],
            today=date(2026, 5, 8),
        )
        old = compute_pulse(
            [PulseInput(polarity=1.0, published_on=date(2026, 4, 23))],
            today=date(2026, 5, 8),
        )
        # 15 days = 3 half-lives at τ=5
        assert old.score < recent.score / 5
        assert recent.score > 0


# ── Pump/dump rule ─────────────────────────────────────────────────────


class TestPumpDump:
    def _normal_bar(self, vol: float = 1_000_000.0, price: float = 100.0) -> DailyBar:
        return DailyBar(
            open=price,
            high=price * 1.01,
            low=price * 0.99,
            close=price,
            volume=vol,
            prev_close=price,
        )

    def test_normal_day_no_trigger(self) -> None:
        bar = self._normal_bar()
        result = detect_rule(bar, vol_ma_20=1_000_000.0)
        assert not result.triggered

    def test_pump_pattern_triggers(self) -> None:
        bar = DailyBar(
            open=100.0,
            high=110.0,
            low=99.0,
            close=108.0,  # +8%
            volume=6_000_000.0,  # 6× MA
            prev_close=100.0,
        )
        result = detect_rule(bar, vol_ma_20=1_000_000.0)
        assert result.triggered
        assert result.alert_type == "pump"

    def test_dump_pattern_triggers(self) -> None:
        bar = DailyBar(
            open=100.0,
            high=101.0,
            low=88.0,
            close=92.0,  # -8%
            volume=6_000_000.0,
            prev_close=100.0,
        )
        result = detect_rule(bar, vol_ma_20=1_000_000.0)
        assert result.triggered
        assert result.alert_type == "dump"

    def test_volume_spike_without_price_move_no_trigger(self) -> None:
        bar = DailyBar(
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,  # only +0.5%
            volume=10_000_000.0,
            prev_close=100.0,
        )
        result = detect_rule(bar, vol_ma_20=1_000_000.0)
        assert not result.triggered

    def test_anomaly_score_normal_history(self) -> None:
        bars = [self._normal_bar() for _ in range(40)]
        feats = [features_from(b, 1_000_000.0) for b in bars]
        score = anomaly_score(feats[-1], feats[:-1])
        # All identical → no variance → score is 0
        assert score == 0.0

    def test_anomaly_score_extreme_day(self) -> None:
        # History needs some variance for z-scores to be meaningful — we
        # vary volume + close slightly across the window.
        import random
        random.seed(42)
        normal_bars: list[DailyBar] = []
        prev = 100.0
        for _ in range(40):
            close = prev * (1 + (random.random() - 0.5) * 0.02)  # ±1%
            normal_bars.append(
                DailyBar(
                    open=prev,
                    high=max(prev, close) * 1.005,
                    low=min(prev, close) * 0.995,
                    close=close,
                    volume=900_000 + random.random() * 200_000,
                    prev_close=prev,
                )
            )
            prev = close

        spike = DailyBar(
            open=prev,
            high=prev * 1.30,
            low=prev * 0.99,
            close=prev * 1.25,
            volume=20_000_000.0,
            prev_close=prev,
        )
        feats_history = [features_from(b, 1_000_000.0) for b in normal_bars]
        feat_today = features_from(spike, 1_000_000.0)
        score = anomaly_score(feat_today, feats_history)
        assert score > 5.0

    def test_severity_high_no_news_context(self) -> None:
        sev = escalate_severity(
            rule_triggered=True,
            anomaly_score_value=4.5,
            has_announcement_today=False,
            has_high_impact_news_today=False,
            sentiment_pulse=0.0,
        )
        assert sev == "high"

    def test_severity_news_context_downgrades(self) -> None:
        sev = escalate_severity(
            rule_triggered=True,
            anomaly_score_value=2.0,
            has_announcement_today=True,
            has_high_impact_news_today=False,
            sentiment_pulse=70.0,  # strongly positive news
        )
        assert sev == "low"
