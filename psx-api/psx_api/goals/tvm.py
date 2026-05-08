"""
Time-value-of-money math for the Goal engine.

Given a target amount, current savings, monthly contribution and target date,
solve for the **annual** rate (CAGR) the portfolio must earn for the user to
land on the target. We can't solve in closed form (FV-of-annuity + FV-of-PV
combined isn't analytically invertible for `r`), so we bisect on a wide
bracket — fast, deterministic, no numpy.

Realism rating
==============

Once we know required CAGR we score it as one of:
  - feasible      ≤ 8%      below long-run T-Bill yield in PKR
  - stretch       8–14%     KSE-100 long-run is ~14% nominal
  - aggressive    14–20%    only top decile of stocks deliver this sustained
  - unrealistic   > 20%     long-run sustained means the goal needs more time / money

The thresholds bake in Pakistani context (high inflation + nominal returns).
Phase 3 will refine these with current KIBOR + CPI feeds.

Pure functions, Decimal in/out. No DB or framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


Rating = Literal["feasible", "stretch", "aggressive", "unrealistic", "already_funded"]


@dataclass(frozen=True)
class GoalAnalysis:
    months_remaining: int
    years_remaining: float
    required_cagr: Decimal | None  # None when already funded or impossible to reach
    rating: Rating
    summary: str
    suggested_monthly_contribution_pkr: Decimal | None  # to land at "stretch" rate
    suggested_extension_months: int | None  # to land at "feasible" rate


# ── helpers ─────────────────────────────────────────────────────────────


def _months_between(start: date, end: date) -> int:
    """End-of-month aware month count, never negative."""
    if end <= start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def _future_value(
    *,
    present_value: float,
    monthly_contribution: float,
    months: int,
    annual_rate: float,
) -> float:
    """
    FV with end-of-month contributions.

      FV = PV * (1+r)^n  +  PMT * [((1+r)^n - 1) / r]

    where r = monthly rate, n = number of months.
    """
    if months == 0:
        return present_value
    if annual_rate == 0:
        return present_value + monthly_contribution * months
    r = annual_rate / 12
    growth = (1 + r) ** months
    return present_value * growth + monthly_contribution * (growth - 1) / r


def _bisect_cagr(
    *,
    target: float,
    present_value: float,
    monthly_contribution: float,
    months: int,
) -> float | None:
    """
    Solve `_future_value(... rate) == target` for `rate`.

    Returns the required annual rate, or None if unreachable in any sane range.
    Bracket [-50%, +200%] catches even pathological inputs.
    """
    if months == 0:
        return None
    lo, hi = -0.5, 2.0
    fv_lo = _future_value(
        present_value=present_value,
        monthly_contribution=monthly_contribution,
        months=months,
        annual_rate=lo,
    )
    fv_hi = _future_value(
        present_value=present_value,
        monthly_contribution=monthly_contribution,
        months=months,
        annual_rate=hi,
    )
    if target < fv_lo or target > fv_hi:
        return None
    # 60 iterations of bisection on a 250-percentage-point range gets us to
    # well below 1e-15 precision — overkill but cheap.
    for _ in range(80):
        mid = (lo + hi) / 2
        fv_mid = _future_value(
            present_value=present_value,
            monthly_contribution=monthly_contribution,
            months=months,
            annual_rate=mid,
        )
        if fv_mid < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _rating_for_cagr(cagr_pct: float) -> Rating:
    if cagr_pct <= 8:
        return "feasible"
    if cagr_pct <= 14:
        return "stretch"
    if cagr_pct <= 20:
        return "aggressive"
    return "unrealistic"


# ── Public API ──────────────────────────────────────────────────────────


def analyze(
    *,
    target_amount_pkr: Decimal,
    current_amount_pkr: Decimal,
    monthly_contribution_pkr: Decimal,
    target_date: date,
    today: date,
) -> GoalAnalysis:
    """Run the full analysis pipeline and return a GoalAnalysis."""
    target = float(target_amount_pkr)
    pv = float(current_amount_pkr)
    pmt = float(monthly_contribution_pkr)
    months = _months_between(today, target_date)
    years = months / 12.0

    if pv >= target:
        return GoalAnalysis(
            months_remaining=months,
            years_remaining=round(years, 2),
            required_cagr=None,
            rating="already_funded",
            summary=(
                f"You're already at PKR {pv:,.0f} against a target of "
                f"PKR {target:,.0f}. Goal is funded — keep it invested."
            ),
            suggested_monthly_contribution_pkr=None,
            suggested_extension_months=None,
        )

    if months == 0:
        return GoalAnalysis(
            months_remaining=0,
            years_remaining=0,
            required_cagr=None,
            rating="unrealistic",
            summary=(
                f"Target date is today or in the past, but you're PKR "
                f"{target - pv:,.0f} short. Pick a future target date."
            ),
            suggested_monthly_contribution_pkr=None,
            suggested_extension_months=None,
        )

    rate = _bisect_cagr(
        target=target,
        present_value=pv,
        monthly_contribution=pmt,
        months=months,
    )

    if rate is None:
        return GoalAnalysis(
            months_remaining=months,
            years_remaining=round(years, 2),
            required_cagr=None,
            rating="unrealistic",
            summary=(
                "Even at extreme growth rates, your current contribution "
                "doesn't reach this target. Increase the monthly contribution."
            ),
            suggested_monthly_contribution_pkr=Decimal(
                str(round(_required_pmt(target=target, pv=pv, months=months, rate=0.12), 2))
            ),
            suggested_extension_months=12,
        )

    cagr_pct = round(rate * 100, 2)
    rating = _rating_for_cagr(cagr_pct)

    summary = _summary_for(cagr_pct, rating, target, pv, pmt, years)

    suggested_pmt = None
    suggested_ext = None
    if rating in ("aggressive", "unrealistic"):
        # PMT to hit "stretch" (10%) at current horizon
        suggested_pmt = Decimal(
            str(round(_required_pmt(target=target, pv=pv, months=months, rate=0.10), 2))
        )
        # Months extension to drop required CAGR to "feasible" 8% at current PMT
        ext = _months_to_drop_to_feasible(target=target, pv=pv, pmt=pmt, rate=0.08)
        if ext is not None:
            suggested_ext = max(0, ext - months)

    return GoalAnalysis(
        months_remaining=months,
        years_remaining=round(years, 2),
        required_cagr=Decimal(str(cagr_pct)),
        rating=rating,
        summary=summary,
        suggested_monthly_contribution_pkr=suggested_pmt,
        suggested_extension_months=suggested_ext,
    )


def _required_pmt(*, target: float, pv: float, months: int, rate: float) -> float:
    """Solve FV equation for PMT given a fixed rate."""
    if months == 0:
        return 0
    if rate == 0:
        return max(0.0, (target - pv) / months)
    r = rate / 12
    growth = (1 + r) ** months
    pv_grown = pv * growth
    deficit = target - pv_grown
    if deficit <= 0:
        return 0
    return deficit * r / (growth - 1)


def _months_to_drop_to_feasible(
    *, target: float, pv: float, pmt: float, rate: float
) -> int | None:
    """How many months to extend so that `rate` (e.g. 8%) is enough?"""
    # Walk months out and stop when FV at `rate` exceeds target.
    for months in range(1, 12 * 60):  # cap at 60 yrs
        fv = _future_value(
            present_value=pv,
            monthly_contribution=pmt,
            months=months,
            annual_rate=rate,
        )
        if fv >= target:
            return months
    return None


def _summary_for(
    cagr_pct: float, rating: Rating, target: float, pv: float, pmt: float, years: float
) -> str:
    horizon = f"{years:.1f} year{'s' if years != 1 else ''}"
    if rating == "feasible":
        return (
            f"You need {cagr_pct:.1f}% CAGR — comfortably below long-run "
            f"PKR T-Bill yields. Realistic with a conservative or balanced mix over {horizon}."
        )
    if rating == "stretch":
        return (
            f"You need {cagr_pct:.1f}% CAGR over {horizon}. Achievable with a diversified "
            "PSX equity portfolio in line with KSE-100's long-run nominal return, but "
            "not guaranteed — expect 20–30% drawdowns along the way."
        )
    if rating == "aggressive":
        return (
            f"You need {cagr_pct:.1f}% CAGR over {horizon} — only the top decile of stocks "
            "sustain this. Either accept a lot of single-stock risk, increase your monthly "
            "contribution, or push the deadline out."
        )
    return (
        f"You need {cagr_pct:.1f}% CAGR over {horizon} — unrealistic for the long term. "
        "Increase your monthly contribution or extend the deadline; the math here is "
        "fighting you."
    )
