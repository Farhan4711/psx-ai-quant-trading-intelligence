"""
Pump-and-dump detector — three layers per build plan Steps 54–56.

  Layer 1 (rule-based): volume spike × price change. A day with volume
    >4× the 20-day moving average AND |price_change| >3% gets a base
    flag. This is the SECP-recognised "coordinated price + volume"
    pattern that anchors most academic detection literature.

  Layer 2 (statistical anomaly): per-stock z-score across 6 features.
    The spec calls for sklearn IsolationForest with 2% contamination,
    but that's a 100+ MB sklearn dep we don't yet ship. The contract is
    the same — `anomaly_score` ∈ [0, ∞], higher = more anomalous —
    and the v1 implementation uses the L2 norm of feature z-scores
    against the trailing 60-day window. When sklearn lands, swap the
    body of `anomaly_score()` and nothing else changes.

  Layer 3 (news-correlation filter): a pure spike with no news context
    is more suspicious than one on earnings day. Caller passes in
    has_announcement_today + has_news_today + sentiment_pulse and
    `escalate_severity()` decides low / medium / high.

All pure functions. Service layer (psx_api.services.alert_service) does
the DB I/O and persistence to suspicious_days.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt

# ── Layer 1: rule-based ────────────────────────────────────────────────


@dataclass(frozen=True)
class DailyBar:
    """Inputs Layer 1 needs. `prev_close` is yesterday's close (for gap)."""

    open: float
    high: float
    low: float
    close: float
    volume: float
    prev_close: float | None


@dataclass(frozen=True)
class RuleResult:
    triggered: bool
    alert_type: str | None  # "pump" | "dump" | None
    vol_spike: float
    price_change_pct: float
    explanation: str


# Thresholds straight from the build plan
_VOL_SPIKE_THRESHOLD = 4.0
_PRICE_CHANGE_THRESHOLD = 0.03


def detect_rule(today: DailyBar, vol_ma_20: float) -> RuleResult:
    """
    Layer 1: 4× volume + 3% price-change rule.
    `vol_ma_20` is the trailing-20-day mean volume excluding `today`.
    """
    vol_spike = today.volume / vol_ma_20 if vol_ma_20 > 0 else 0.0
    price_change = (today.close - today.open) / today.open if today.open > 0 else 0.0

    if vol_spike >= _VOL_SPIKE_THRESHOLD:
        if price_change >= _PRICE_CHANGE_THRESHOLD:
            return RuleResult(
                triggered=True,
                alert_type="pump",
                vol_spike=round(vol_spike, 2),
                price_change_pct=round(price_change * 100, 2),
                explanation=(
                    f"Volume today is {vol_spike:.1f}× the 20-day average "
                    f"with a {price_change * 100:.1f}% price increase — "
                    "the textbook pump pattern."
                ),
            )
        if price_change <= -_PRICE_CHANGE_THRESHOLD:
            return RuleResult(
                triggered=True,
                alert_type="dump",
                vol_spike=round(vol_spike, 2),
                price_change_pct=round(price_change * 100, 2),
                explanation=(
                    f"Volume today is {vol_spike:.1f}× the 20-day average "
                    f"with a {abs(price_change) * 100:.1f}% drop — "
                    "the textbook dump pattern."
                ),
            )

    return RuleResult(
        triggered=False,
        alert_type=None,
        vol_spike=round(vol_spike, 2),
        price_change_pct=round(price_change * 100, 2),
        explanation="No rule-based pump/dump signal.",
    )


# ── Layer 2: statistical anomaly ───────────────────────────────────────


@dataclass(frozen=True)
class AnomalyFeatures:
    close: float
    volume: float
    vol_spike: float
    price_change_pct: float  # already in percent
    intraday_range_pct: float  # (high - low) / open * 100
    gap_pct: float  # (open - prev_close) / prev_close * 100


def features_from(bar: DailyBar, vol_ma_20: float) -> AnomalyFeatures:
    """Build the 6-feature anomaly input from one bar."""
    vol_spike = bar.volume / vol_ma_20 if vol_ma_20 > 0 else 0.0
    pc = (bar.close - bar.open) / bar.open * 100 if bar.open > 0 else 0.0
    range_pct = (bar.high - bar.low) / bar.open * 100 if bar.open > 0 else 0.0
    gap_pct = (bar.open - bar.prev_close) / bar.prev_close * 100 if bar.prev_close else 0.0
    return AnomalyFeatures(
        close=bar.close,
        volume=bar.volume,
        vol_spike=vol_spike,
        price_change_pct=pc,
        intraday_range_pct=range_pct,
        gap_pct=gap_pct,
    )


def anomaly_score(today: AnomalyFeatures, history: Sequence[AnomalyFeatures]) -> float:
    """
    Z-score-norm anomaly score against the trailing window.

    L2 of per-feature standardised distances. ~0 for a normal day,
    >3 for a 3-sigma move on multiple features at once.
    """
    if len(history) < 5:
        return 0.0

    fields = (
        "close",
        "volume",
        "vol_spike",
        "price_change_pct",
        "intraday_range_pct",
        "gap_pct",
    )
    sq_sum = 0.0
    for field in fields:
        values = [getattr(h, field) for h in history]
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
        std = sqrt(var) if var > 0 else 0.0
        if std == 0:
            continue
        z = (getattr(today, field) - mean) / std
        sq_sum += z * z
    return round(sqrt(sq_sum), 4)


# ── Layer 3: news-correlation filter ───────────────────────────────────


def escalate_severity(
    rule_triggered: bool,
    anomaly_score_value: float,
    has_announcement_today: bool,
    has_high_impact_news_today: bool,
    sentiment_pulse: float,
) -> str:
    """
    Combine layers 1+2 with the news/announcement context to assign
    final severity. Returns one of: "low" | "medium" | "high".
    """
    # If news context explains the move, downgrade or suppress
    news_context = has_announcement_today or has_high_impact_news_today

    if rule_triggered and not news_context:
        # Pure spike, no context: most suspicious
        if anomaly_score_value >= 4.0:
            return "high"
        if anomaly_score_value >= 2.5:
            return "high"
        return "medium"

    if rule_triggered and news_context:
        # Strong pump/dump but sentiment justifies it: medium → low scale
        if abs(sentiment_pulse) > 50:
            return "low"
        return "medium"

    # Layer 1 didn't trigger but anomaly is loud
    if anomaly_score_value >= 5.0 and not news_context:
        return "medium"

    return "low"
