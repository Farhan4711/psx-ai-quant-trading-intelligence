"""
Bucketing for anonymized benchmarking (Phase 4 Step 60).

Three independent axes — archetype × age × portfolio size — produce a
peer-group key. Buckets are deliberately coarse so individual users
can't be re-identified by triangulating their bucket assignments.

  age:        18-24 / 25-34 / 35-44 / 45-54 / 55+
  size:       <100K / 100K-500K / 500K-2M / 2M-10M / 10M+ (PKR)
  archetype:  the 5 risk profiles from Phase 2A

Privacy: aggregates with sample_count < 5 are suppressed. The benchmark
endpoint hides the panel entirely if the user's bucket has fewer than
5 contributing peers.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal


MIN_BUCKET_SAMPLES = 5  # k-anonymity floor


def age_bucket(dob: date | None, today: date | None = None) -> str:
    if dob is None:
        return "unknown"
    today = today or date.today()
    years = today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )
    if years < 25:
        return "18-24"
    if years < 35:
        return "25-34"
    if years < 45:
        return "35-44"
    if years < 55:
        return "45-54"
    return "55+"


def size_bucket(portfolio_value_pkr: Decimal | float | None) -> str:
    if portfolio_value_pkr is None:
        return "unknown"
    v = float(portfolio_value_pkr)
    if v < 100_000:
        return "<100K"
    if v < 500_000:
        return "100K-500K"
    if v < 2_000_000:
        return "500K-2M"
    if v < 10_000_000:
        return "2M-10M"
    return "10M+"


def archetype_bucket(archetype: str | None) -> str:
    return archetype or "unknown"


def bucket_label(archetype: str, age: str, size: str) -> str:
    """Human-readable label for the UI panel header."""
    pretty_arche = archetype.replace("_", " ").title() if archetype != "unknown" else "Unspecified profile"
    age_str = "Unknown age" if age == "unknown" else age
    size_str = "Unknown portfolio size" if size == "unknown" else size + " PKR"
    return f"{pretty_arche} · {age_str} · {size_str}"


def percentile_rank(value: float, distribution: list[float]) -> int:
    """How many percent of `distribution` is below `value` (0..100)."""
    if not distribution:
        return 50
    below = sum(1 for v in distribution if v < value)
    return round(below / len(distribution) * 100)
