"""
News Pulse: rolling sentiment score per symbol with exponential time decay.

Per build plan Step 52:
  pulse(symbol, today) = Σ[ polarity_i * exp(-(today - pub_date_i) / 5) ]

Normalised to [-100, +100] for display. We multiply by a saturation
constant so that 5–10 strongly-polar headlines drive the score to ±70+
and one stale headline doesn't move it past ~10. Pure math; the service
layer handles loading article_sentiment rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import exp

# Half-life: 5 days. The exp decay below uses τ=5 directly (not "half"),
# so a 5-day-old headline is weighted ~37% of a same-day headline.
_DECAY_TAU_DAYS = 5

# Saturation constant. 10 same-day articles at full +1 polarity gets us to
# ~+90 (well below the +100 cap so the top of the scale is reachable but
# not common).
_SATURATION = 9.0


@dataclass(frozen=True)
class PulseInput:
    polarity: float  # in [-1, +1]
    published_on: date


@dataclass(frozen=True)
class PulseScore:
    score: float  # in [-100, +100]
    article_count: int
    weighted_count: float


def compute_pulse(items: list[PulseInput], *, today: date) -> PulseScore:
    """Single-symbol pulse score."""
    if not items:
        return PulseScore(score=0.0, article_count=0, weighted_count=0.0)

    weighted_sum = 0.0
    total_weight = 0.0
    for item in items:
        days_old = max(0, (today - item.published_on).days)
        weight = exp(-days_old / _DECAY_TAU_DAYS)
        weighted_sum += item.polarity * weight
        total_weight += weight

    # Bring to [-100, +100] using saturation. A strongly negative
    # weighted_sum of about -_SATURATION gets us to -100; smaller magnitudes
    # scale linearly.
    raw = (weighted_sum / _SATURATION) * 100
    score = max(-100.0, min(100.0, raw))
    return PulseScore(
        score=round(score, 1),
        article_count=len(items),
        weighted_count=round(total_weight, 2),
    )
