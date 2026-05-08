"""
Recommended target allocation per (archetype, time horizon).

Phase 2 v1: simple lookup table (per build plan Step 36). Phase 3 will
replace this with Markowitz mean-variance optimisation; the API stays the
same so callers don't churn.

Asset classes for v1:
  - equity      → PSX equities (KSE-100 / KMI-30 mix)
  - tbills      → 3-month T-Bills (or Sukuk for Shariah users)
  - cash        → bank savings buffer

For horizons measured in months. Buckets per the build-plan grid:
  <2y, 2–5y, 5–10y, >10y.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


HorizonBucket = Literal["short", "medium", "long", "very_long"]


def horizon_bucket(months: int) -> HorizonBucket:
    if months < 24:
        return "short"
    if months < 60:
        return "medium"
    if months < 120:
        return "long"
    return "very_long"


# Each tuple is (equity_pct, tbills_pct, cash_pct) — must sum to 100.
_TABLE: dict[str, dict[HorizonBucket, tuple[int, int, int]]] = {
    "conservative_saver": {
        "short":     (0,   90, 10),
        "medium":    (30,  65, 5),
        "long":      (50,  47, 3),
        "very_long": (60,  37, 3),
    },
    "cautious_beginner": {
        "short":     (10,  80, 10),
        "medium":    (40,  55, 5),
        "long":      (60,  37, 3),
        "very_long": (70,  27, 3),
    },
    "balanced_builder": {
        "short":     (30,  60, 10),
        "medium":    (50,  47, 3),
        "long":      (70,  27, 3),
        "very_long": (80,  17, 3),
    },
    "growth_seeker": {
        "short":     (40,  55, 5),
        "medium":    (65,  32, 3),
        "long":      (85,  12, 3),
        "very_long": (95,   3, 2),
    },
    "aggressive_trader": {
        "short":     (50,  45, 5),
        "medium":    (70,  27, 3),
        "long":      (90,   8, 2),
        "very_long": (100,  0, 0),
    },
}


@dataclass(frozen=True)
class Allocation:
    archetype: str
    horizon_bucket: HorizonBucket
    months: int
    equity_pct: int
    tbills_pct: int
    cash_pct: int
    rationale: str


_BUCKET_LABELS: dict[HorizonBucket, str] = {
    "short": "<2 years",
    "medium": "2–5 years",
    "long": "5–10 years",
    "very_long": "10+ years",
}


def recommend(*, archetype: str, months_remaining: int) -> Allocation:
    bucket = horizon_bucket(months_remaining)
    if archetype not in _TABLE:
        # Unknown archetype (e.g. user hasn't taken the quiz) → balanced default
        archetype = "balanced_builder"
    eq, tb, cash = _TABLE[archetype][bucket]

    rationale = _rationale_for(archetype, bucket, eq)
    return Allocation(
        archetype=archetype,
        horizon_bucket=bucket,
        months=months_remaining,
        equity_pct=eq,
        tbills_pct=tb,
        cash_pct=cash,
        rationale=rationale,
    )


def _rationale_for(archetype: str, bucket: HorizonBucket, equity_pct: int) -> str:
    horizon_label = _BUCKET_LABELS[bucket]
    if equity_pct == 0:
        return (
            f"With a {horizon_label} horizon and a {archetype.replace('_', ' ')} "
            "profile, equity drawdowns would have nowhere to recover. T-Bills "
            "and cash protect the principal."
        )
    if equity_pct >= 90:
        return (
            f"A {horizon_label} horizon gives equity drawdowns plenty of time "
            "to recover. For your profile, the long-run real-return premium "
            "from equities outweighs the volatility cost."
        )
    return (
        f"A {horizon_label} horizon and {archetype.replace('_', ' ')} profile "
        f"point to a balanced split: {equity_pct}% equity for growth, the rest "
        "in T-Bills/Sukuk for stability through drawdowns."
    )
