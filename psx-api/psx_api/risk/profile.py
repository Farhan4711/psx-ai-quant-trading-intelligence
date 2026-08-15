"""
Risk-profile questionnaire content and scoring.

Pure data + pure functions. The DB stores axis scores + final archetype on
the user row; this module owns the question text, the per-option weights,
and the archetype mapping. Keep it pure so it's trivially testable and the
question set can evolve without breaking persisted profiles.

Three axes, scored 1–5:
  - risk_tolerance  (5 questions, max 25 → normalised 1..5)
  - time_horizon    (3 questions, max 15 → normalised 1..5)
  - knowledge       (4 questions; right answers worth 5, wrong 1)

Archetype = function of (tolerance, horizon, knowledge). See `archetype()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Axis = Literal["risk_tolerance", "time_horizon", "knowledge"]


@dataclass(frozen=True)
class Option:
    value: str  # stable ID, persisted in answers
    label: str  # user-facing
    weight: int  # 1–5; for knowledge questions, only the correct answer is 5


@dataclass(frozen=True)
class Question:
    id: str
    axis: Axis
    prompt: str
    options: tuple[Option, ...]


# ── Question bank ──────────────────────────────────────────────────────


QUESTIONS: tuple[Question, ...] = (
    # ── Risk tolerance (5) ────────────────────────────────────────
    Question(
        id="rt1",
        axis="risk_tolerance",
        prompt="If your portfolio dropped 30% in a single month, what would you do?",
        options=(
            Option("sell_all", "Sell everything to stop the bleeding", 1),
            Option("sell_some", "Sell some to reduce exposure", 2),
            Option("hold", "Hold and wait for recovery", 4),
            Option("buy_more", "Buy more — the dip is an opportunity", 5),
        ),
    ),
    Question(
        id="rt2",
        axis="risk_tolerance",
        prompt="Pick the portfolio you'd be most comfortable owning.",
        options=(
            Option("a", "Average return 4%, worst year ‑2%", 1),
            Option("b", "Average return 7%, worst year ‑10%", 2),
            Option("c", "Average return 10%, worst year ‑20%", 3),
            Option("d", "Average return 14%, worst year ‑35%", 4),
            Option("e", "Average return 20%, worst year ‑50%", 5),
        ),
    ),
    Question(
        id="rt3",
        axis="risk_tolerance",
        prompt="How would you describe your investing experience so far?",
        options=(
            Option("none", "I haven't invested before", 1),
            Option("savings", "Mostly savings accounts and fixed deposits", 2),
            Option("mutual_funds", "Mutual funds / Sukuk", 3),
            Option("equities", "Direct equities", 4),
            Option("active", "Active equities, options, or futures", 5),
        ),
    ),
    Question(
        id="rt4",
        axis="risk_tolerance",
        prompt="What share of your monthly income could you put at meaningful risk?",
        options=(
            Option("0_5", "0–5%", 1),
            Option("5_10", "5–10%", 2),
            Option("10_20", "10–20%", 3),
            Option("20_30", "20–30%", 4),
            Option("30_plus", "30%+", 5),
        ),
    ),
    Question(
        id="rt5",
        axis="risk_tolerance",
        prompt="How would you feel checking your portfolio after a -15% week?",
        options=(
            Option("panic", "Panicked — I'd want out", 1),
            Option("uneasy", "Uneasy but I'd hold", 2),
            Option("ok", "It's part of the game", 4),
            Option("excited", "Excited — time to buy", 5),
        ),
    ),
    # ── Time horizon (3) ──────────────────────────────────────────
    Question(
        id="th1",
        axis="time_horizon",
        prompt="When will you most likely need this money?",
        options=(
            Option("lt2", "Within 2 years", 1),
            Option("2_5", "2–5 years", 2),
            Option("5_10", "5–10 years", 3),
            Option("10_20", "10–20 years", 4),
            Option("20_plus", "20+ years (retirement, legacy)", 5),
        ),
    ),
    Question(
        id="th2",
        axis="time_horizon",
        prompt="Could you live without this money for 5+ years if a crash forced you to wait?",
        options=(
            Option("no", "No, I'd need it sooner", 1),
            Option("maybe", "Maybe — would be tight", 3),
            Option("yes", "Yes, comfortably", 5),
        ),
    ),
    Question(
        id="th3",
        axis="time_horizon",
        prompt="Are you currently saving toward a specific goal that has a hard deadline?",
        options=(
            Option("hard_soon", "Yes, within 3 years (down payment, wedding, Hajj)", 1),
            Option("medium", "Yes, in 3–10 years", 3),
            Option("flexible", "No hard deadline — long-term wealth building", 5),
        ),
    ),
    # ── Knowledge (4) ─────────────────────────────────────────────
    # Each correct answer = 5; everything else = 1.
    Question(
        id="kn1",
        axis="knowledge",
        prompt="What is the KMI-30 index?",
        options=(
            Option("top30", "The 30 largest stocks on PSX", 1),
            Option("kmi", "The 30 largest Shariah-compliant stocks on PSX", 5),
            Option("top100", "Same as KSE-100 minus banks", 1),
            Option("dontknow", "Not sure", 1),
        ),
    ),
    Question(
        id="kn2",
        axis="knowledge",
        prompt="What does CGT stand for and when does it apply?",
        options=(
            Option("right", "Capital Gains Tax — paid on realised profit when you sell", 5),
            Option("wrong1", "Capital Growth Tax — paid annually on holdings", 1),
            Option("wrong2", "Cumulative Gain Tax — paid on dividends only", 1),
            Option("dontknow", "Not sure", 1),
        ),
    ),
    Question(
        id="kn3",
        axis="knowledge",
        prompt="If a stock's P/E ratio is much higher than its sector average, that usually means…",
        options=(
            Option(
                "right", "The market is pricing in higher future growth (or it's overvalued)", 5
            ),
            Option("wrong1", "It's safer than the rest of the sector", 1),
            Option("wrong2", "It pays a higher dividend", 1),
            Option("dontknow", "Not sure", 1),
        ),
    ),
    Question(
        id="kn4",
        axis="knowledge",
        prompt="Diversification primarily reduces which kind of risk?",
        options=(
            Option("right", "Stock-specific (idiosyncratic) risk", 5),
            Option("wrong1", "All risk equally", 1),
            Option("wrong2", "Inflation risk", 1),
            Option("dontknow", "Not sure", 1),
        ),
    ),
)


# ── Scoring ────────────────────────────────────────────────────────────


_BY_ID = {q.id: q for q in QUESTIONS}


class InvalidAnswersError(ValueError):
    """Raised when the answer dict is missing questions or has unknown options."""


def score(answers: dict[str, str]) -> dict[str, int]:
    """
    Returns axis scores normalised to 1..5 inclusive.

    `answers` maps question_id → option.value. Every question must be answered.
    """
    if set(answers.keys()) != set(_BY_ID.keys()):
        missing = set(_BY_ID.keys()) - set(answers.keys())
        extra = set(answers.keys()) - set(_BY_ID.keys())
        raise InvalidAnswersError(
            f"Answer set mismatch — missing: {sorted(missing)}, unknown: {sorted(extra)}"
        )

    raw: dict[Axis, list[int]] = {"risk_tolerance": [], "time_horizon": [], "knowledge": []}
    for qid, value in answers.items():
        q = _BY_ID[qid]
        opt = next((o for o in q.options if o.value == value), None)
        if opt is None:
            raise InvalidAnswersError(f"Unknown option '{value}' for question '{qid}'")
        raw[q.axis].append(opt.weight)

    # Average → round to nearest int → clamp 1..5
    return {
        axis: max(1, min(5, round(sum(weights) / len(weights)))) for axis, weights in raw.items()
    }


# ── Archetype mapping ──────────────────────────────────────────────────


ARCHETYPES = (
    "conservative_saver",
    "cautious_beginner",
    "balanced_builder",
    "growth_seeker",
    "aggressive_trader",
)


@dataclass(frozen=True)
class ArchetypeProfile:
    key: str
    label: str
    description: str


ARCHETYPE_PROFILES: dict[str, ArchetypeProfile] = {
    "conservative_saver": ArchetypeProfile(
        "conservative_saver",
        "Conservative Saver",
        "Capital preservation first. T-Bills and Sukuk dominate; equities are a small satellite.",
    ),
    "cautious_beginner": ArchetypeProfile(
        "cautious_beginner",
        "Cautious Beginner",
        "Learning the ropes. A meaningful equity allocation backed by a solid fixed-income base.",
    ),
    "balanced_builder": ArchetypeProfile(
        "balanced_builder",
        "Balanced Builder",
        "Steady wealth-building. Equities and fixed income roughly balanced, tilted by horizon.",
    ),
    "growth_seeker": ArchetypeProfile(
        "growth_seeker",
        "Growth Seeker",
        "Wants real returns over inflation. Equity-heavy, comfortable with multi-year drawdowns.",
    ),
    "aggressive_trader": ArchetypeProfile(
        "aggressive_trader",
        "Aggressive Trader",
        "High volatility tolerance, long horizon, active engagement with markets.",
    ),
}


def archetype(scores: dict[str, int]) -> str:
    """
    Map (tolerance, horizon, knowledge) → archetype.

    Tolerance is the dominant axis. Horizon and knowledge can shift the
    bucket up or down by one. Knowledge alone never elevates someone to
    aggressive — knowing the lingo doesn't equal stomach.
    """
    rt = scores["risk_tolerance"]
    th = scores["time_horizon"]
    kn = scores["knowledge"]

    base = max(0, min(4, rt - 1))  # 0..4 mapped from 1..5
    # Short horizon caps risk
    if th <= 2 and base > 2:
        base = 2
    # Long horizon nudges up by one if knowledge supports it
    if th >= 4 and kn >= 3 and base < 4:
        base += 1
    # Very low knowledge caps at cautious_beginner unless tolerance is very high
    if kn <= 2 and rt < 5 and base > 1:
        base = 1
    return ARCHETYPES[base]


def evaluate(answers: dict[str, str]) -> dict[str, Any]:
    """One-shot: answers → axis scores + archetype + profile description."""
    sc = score(answers)
    arch_key = archetype(sc)
    profile = ARCHETYPE_PROFILES[arch_key]
    return {
        "scores": sc,
        "archetype": arch_key,
        "label": profile.label,
        "description": profile.description,
    }
