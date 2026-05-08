"""
Starter lesson curriculum — 10 short, PSX-specific lessons (Phase 4 Step 66).

Each lesson is a few paragraphs of plain-English markdown plus a
3-question quiz. We seed these into the `lessons` table on first boot
so the skill tree UI works against real rows. The full target is 30+
lessons per the build plan; we ship the highest-impact 10 here and
adopt a content cadence (one new lesson per week) afterwards.

This module is deliberately data-only. The service layer reads it and
upserts into the lessons table; editors can replace the upsert with a
DB-only flow once content gets long.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuizOption:
    text: str
    correct: bool


@dataclass(frozen=True)
class QuizQuestion:
    question: str
    options: list[QuizOption]


@dataclass(frozen=True)
class LessonContent:
    slug: str
    title: str
    category: str       # "basics" | "analysis" | "tax" | "shariah" | "discipline"
    difficulty: int     # 1..3
    body_md: str
    quiz: list[QuizQuestion]


def _q(q: str, *opts: tuple[str, bool]) -> QuizQuestion:
    return QuizQuestion(
        question=q, options=[QuizOption(text=t, correct=c) for t, c in opts]
    )


CURRICULUM: list[LessonContent] = [
    LessonContent(
        slug="what-is-a-stock",
        title="What is a stock?",
        category="basics",
        difficulty=1,
        body_md=(
            "A stock represents partial ownership of a company. When you buy "
            "100 shares of **ENGRO**, you own a tiny slice of Engro "
            "Corporation — entitled to your share of its future profits "
            "(via dividends), your share of any sale of the company, and "
            "your share of votes at the AGM.\n\n"
            "**Why companies issue stock**: it's a way to raise long-term "
            "capital without taking on debt. Instead of borrowing PKR 5 "
            "billion at 18% KIBOR, a company can sell shares to investors "
            "and grow without interest payments.\n\n"
            "**Why people buy stock**: two return streams — capital gains "
            "(price goes up, you sell higher) and dividends (cash payouts "
            "from profits). Over the long run, equities historically beat "
            "fixed deposits and even gold in PKR terms — but with much "
            "more volatility along the way."
        ),
        quiz=[
            _q(
                "When you buy a share of stock, what do you own?",
                ("A loan to the company that pays interest", False),
                ("A small piece of the company itself", True),
                ("A guaranteed monthly payment", False),
                ("Insurance against the company failing", False),
            ),
            _q(
                "What are the two main return streams from owning stock?",
                ("Interest and principal", False),
                ("Dividends and capital gains", True),
                ("Rent and resale value", False),
                ("KIBOR and inflation", False),
            ),
            _q(
                "Why do companies issue stock?",
                ("To take on more debt", False),
                ("To raise long-term capital without interest payments", True),
                ("To force employees to invest", False),
                ("Because SECP requires it", False),
            ),
        ],
    ),
    LessonContent(
        slug="how-psx-trading-works",
        title="How PSX trading works",
        category="basics",
        difficulty=1,
        body_md=(
            "Pakistan Stock Exchange runs **two trading sessions** Monday "
            "to Friday: pre-open (09:15-09:30) and continuous (09:32-15:30, "
            "with a half-hour lunch on Friday). Orders flow through a "
            "broker — there is no direct market access for retail.\n\n"
            "**T+2 settlement**: when you sell on Monday, cash hits your "
            "broker account on Wednesday. When you buy on Monday, the shares "
            "show up Wednesday. This matters when you're calculating your "
            "available buying power.\n\n"
            "**Circuit breakers**: each stock has a 5%/7.5% intraday price "
            "limit (depending on category). The KSE-100 itself triggers a "
            "market halt on big swings."
        ),
        quiz=[
            _q(
                "What does T+2 settlement mean on PSX?",
                ("Trades execute in 2 seconds", False),
                ("Cash and shares settle 2 trading days after the trade", True),
                ("You pay 2% commission", False),
                ("You can hold for max 2 days", False),
            ),
            _q(
                "Can retail investors trade directly on PSX without a broker?",
                ("Yes", False),
                ("No — you must go through a registered broker", True),
                ("Only with PKR > 10M", False),
                ("Only during pre-open", False),
            ),
            _q(
                "What's a circuit breaker?",
                ("A daily commission cap", False),
                ("Price limit that pauses trading on extreme moves", True),
                ("The opening auction", False),
                ("A rule that closes the market on Eid", False),
            ),
        ],
    ),
    LessonContent(
        slug="reading-pe-ratio",
        title="Reading the P/E ratio",
        category="analysis",
        difficulty=2,
        body_md=(
            "**P/E (price-to-earnings)** is the most-watched valuation metric "
            "in equities. It's just price per share divided by earnings per "
            "share. A stock at PKR 200 with EPS of PKR 20 has a P/E of 10.\n\n"
            "**What it tells you**: how many years of current earnings would "
            "be needed to 'pay back' the stock's price. A P/E of 10 means "
            "10 years; a P/E of 30 means the market is paying 30 years of "
            "current profits, betting earnings will grow.\n\n"
            "**On PSX**: the index has historically averaged a P/E of 7-9 "
            "— much lower than developed markets — partly because of "
            "higher KIBOR (more attractive bond yields compete with "
            "equities) and partly political risk discounts.\n\n"
            "**Caveat**: P/E ignores debt. A company with high debt and a "
            "low P/E may look cheap on this metric but be carrying real "
            "leverage risk."
        ),
        quiz=[
            _q(
                "If a stock has a P/E of 15 and EPS of PKR 10, what's the price?",
                ("PKR 15", False),
                ("PKR 150", True),
                ("PKR 25", False),
                ("PKR 1.5", False),
            ),
            _q(
                "A higher P/E typically means…",
                ("The stock is safer", False),
                ("The market expects higher future earnings growth (or it's overvalued)", True),
                ("The stock pays a higher dividend", False),
                ("The company has less debt", False),
            ),
            _q(
                "What does P/E NOT account for?",
                ("Debt levels", True),
                ("Earnings", False),
                ("Stock price", False),
                ("Number of shares outstanding", False),
            ),
        ],
    ),
    LessonContent(
        slug="diversification",
        title="Why diversification matters",
        category="discipline",
        difficulty=1,
        body_md=(
            "Putting all your money in one stock is gambling, not investing. "
            "The math is simple: if any single stock has a 5% chance of "
            "going to zero in any given decade (a generous estimate for a "
            "well-known PSX name), your wealth has the same 5% chance.\n\n"
            "Spread that across **10 uncorrelated stocks** and the chance "
            "that all 10 go to zero is 0.05¹⁰ = essentially zero. This is "
            "called *idiosyncratic risk reduction* — the kind of risk "
            "diversification can eliminate.\n\n"
            "**The catch**: diversification only reduces *single-stock* "
            "risk. It doesn't help against a market-wide crash, currency "
            "devaluation, or a regulatory shock that hits everyone. For "
            "those you need to diversify across asset classes (bonds, "
            "gold, real estate), not just stocks."
        ),
        quiz=[
            _q(
                "What kind of risk does diversification primarily reduce?",
                ("Stock-specific (idiosyncratic) risk", True),
                ("Inflation risk", False),
                ("Currency risk", False),
                ("All risk equally", False),
            ),
            _q(
                "Holding 10 uncorrelated stocks vs 1 stock means…",
                ("Same risk", False),
                ("Much lower chance of losing everything to a single-name failure", True),
                ("Higher fees", False),
                ("Lower expected returns", False),
            ),
            _q(
                "Diversification does NOT protect against…",
                ("A single company going bankrupt", False),
                ("A market-wide crash", True),
                ("A wrong stock pick", False),
                ("Sector rotation", False),
            ),
        ],
    ),
    LessonContent(
        slug="rsi-explained",
        title="What RSI actually measures",
        category="analysis",
        difficulty=2,
        body_md=(
            "**RSI** (Relative Strength Index) is a 0-100 momentum gauge. "
            "It compares the size of recent up-day moves to recent down-day "
            "moves over a window (default 14 days).\n\n"
            "**Above 70**: 'overbought.' Recent gains have been sharp; "
            "historically a pullback or sideways move follows more often "
            "than continued gains.\n\n"
            "**Below 30**: 'oversold.' Recent losses have been sharp; a "
            "bounce becomes more likely.\n\n"
            "**The trap**: RSI can stay overbought (>70) for weeks during "
            "a strong trend. Selling just because RSI is 75 in the middle "
            "of a sustained rally has cost many traders enormous gains. "
            "RSI is a *contributing* signal, never a standalone trade rule."
        ),
        quiz=[
            _q(
                "RSI runs on what scale?",
                ("0-100", True),
                ("-100 to +100", False),
                ("0-1", False),
                ("0-50", False),
            ),
            _q(
                "An RSI reading of 78 traditionally suggests…",
                ("Strong buy", False),
                ("Overbought — pullback risk has increased", True),
                ("The stock will crash tomorrow", False),
                ("RSI can never be that high", False),
            ),
            _q(
                "Should you sell automatically when RSI > 70?",
                ("Yes, always", False),
                ("No — RSI can stay overbought for weeks in strong trends", True),
                ("Only on Mondays", False),
                ("Only if you're a non-filer", False),
            ),
        ],
    ),
    LessonContent(
        slug="psx-tax-basics",
        title="How taxes work on PSX gains",
        category="tax",
        difficulty=2,
        body_md=(
            "Two main taxes hit your trades: **CGT (Capital Gains Tax)** "
            "and minor charges (FED, CVT, brokerage).\n\n"
            "**CGT after the Finance Act 2024** (effective 1 July 2024 for "
            "newly-acquired securities): a flat **15% for filers** and "
            "**45% for non-filers**, regardless of holding period. Older "
            "securities follow the pre-2024 progressive holding-period "
            "schedule.\n\n"
            "**NCCPL deducts CGT at source** — your broker hands NCCPL the "
            "tax money before you ever see it. You don't write a separate "
            "cheque. You will see it on your account statement.\n\n"
            "**Filer status is huge**: the rate jumps from 15% → 45% if "
            "you're not on the FBR Active Taxpayer List. For an active "
            "trader this can be the difference between a profitable year "
            "and a break-even one. Filing your annual return is free; do it."
        ),
        quiz=[
            _q(
                "Under Finance Act 2024, what's the flat CGT rate for filers?",
                ("10%", False),
                ("15%", True),
                ("25%", False),
                ("0% if held > 6 years", False),
            ),
            _q(
                "Who deducts your CGT before it reaches you?",
                ("FBR directly", False),
                ("NCCPL (the central counterparty)", True),
                ("Your bank", False),
                ("You file it manually each quarter", False),
            ),
            _q(
                "Approximately how much higher is non-filer CGT vs filer under FA-2024?",
                ("2× higher", False),
                ("3× higher (15% vs 45%)", True),
                ("Same", False),
                ("0.5× lower", False),
            ),
        ],
    ),
    LessonContent(
        slug="shariah-investing-basics",
        title="Shariah-compliant investing on PSX",
        category="shariah",
        difficulty=2,
        body_md=(
            "**Shariah-compliant equities** exclude companies with revenue "
            "from interest-based banking, alcohol, gambling, conventional "
            "insurance, and certain prohibited industries. Companies must "
            "also pass financial-ratio screens (debt/total assets < 37%, "
            "interest income < 5% of revenue).\n\n"
            "**On PSX**: Meezan Bank publishes the **KMI All-Share Index** "
            "and **KMI-30** based on these criteria, reviewed every 6 "
            "months. Stocks can be added or removed.\n\n"
            "**Purification**: even compliant companies sometimes earn a "
            "small amount of interest on cash deposits. The standard "
            "practice is to **donate 5% of cash dividends** received from "
            "compliant stocks as purification. The capital gain itself is "
            "permissible without purification — only the dividend portion."
        ),
        quiz=[
            _q(
                "Which index lists Shariah-compliant PSX stocks?",
                ("KSE-100", False),
                ("KMI-30 / KMI All-Share", True),
                ("PSX-30", False),
                ("Banks-100", False),
            ),
            _q(
                "What's the typical purification rate on KMI dividends?",
                ("0%", False),
                ("5% of cash dividends", True),
                ("100%", False),
                ("Same as CGT", False),
            ),
            _q(
                "Does purification apply to capital gains too?",
                ("Yes, on the full sale price", False),
                ("No — the price-gain itself is permissible without purification", True),
                ("Only on bonus shares", False),
                ("Only for non-filers", False),
            ),
        ],
    ),
    LessonContent(
        slug="position-sizing",
        title="Position sizing — how much to put in one trade",
        category="discipline",
        difficulty=2,
        body_md=(
            "**The single most important rule**: never bet so much on one "
            "trade that being wrong wipes out your account.\n\n"
            "A simple framework: **risk 1-2% of total capital per trade**. "
            "If your portfolio is PKR 500,000 and you set a stop-loss 10% "
            "below entry, your position size is:\n\n"
            "  - 1% of 500,000 = 5,000 PKR risk budget\n"
            "  - 5,000 / (10% stop) = PKR 50,000 position size\n\n"
            "That's 10% of capital in the trade. Doesn't feel like much? "
            "That's the point. Survivable losses keep you in the game long "
            "enough to learn. Account-killers end careers in week one."
        ),
        quiz=[
            _q(
                "A common rule for max risk per trade?",
                ("50% of capital", False),
                ("1-2% of capital", True),
                ("100% of capital", False),
                ("Whatever your gut says", False),
            ),
            _q(
                "If you risk 2% of a PKR 1M portfolio with a 5% stop, what's the position size?",
                ("PKR 100,000", False),
                ("PKR 400,000", True),
                ("PKR 1,000,000", False),
                ("PKR 50,000", False),
            ),
            _q(
                "Why does small position sizing matter?",
                ("Brokers reward it", False),
                ("It keeps individual losses survivable so you stay in the game long enough to learn", True),
                ("It minimises taxes", False),
                ("It's required by SECP", False),
            ),
        ],
    ),
    LessonContent(
        slug="bonus-vs-rights-vs-dividend",
        title="Bonus shares, rights issues, and dividends",
        category="basics",
        difficulty=2,
        body_md=(
            "Three forms of corporate distribution you'll see on PSX:\n\n"
            "**Cash dividend**: company pays you PKR per share owned. "
            "Cash hits your account on the payment date. Taxed at source.\n\n"
            "**Bonus shares**: company issues new shares from retained "
            "earnings, distributed pro-rata. Your share count goes up but "
            "the price-per-share drops proportionally — your total "
            "ownership value is unchanged on day one. **Buying bonus "
            "shares before the ex-date** is a common misconception that "
            "doesn't actually create wealth.\n\n"
            "**Rights issue**: company offers existing shareholders the "
            "right to buy *more* shares at a discounted price. You can "
            "subscribe (commit cash) or sell the rights letter. Ignoring "
            "rights you've been allotted is throwing away free option value."
        ),
        quiz=[
            _q(
                "Bonus shares — does receiving them increase the value of your holding immediately?",
                ("Yes, free shares = free money", False),
                ("No — share count goes up but price drops proportionally; total value unchanged on day 1", True),
                ("Only for filers", False),
                ("Only if you sell within 24 hours", False),
            ),
            _q(
                "What is a rights issue?",
                ("A free distribution of new shares", False),
                ("An offer to buy MORE shares at a discounted price", True),
                ("A vote on board members", False),
                ("A tax refund", False),
            ),
            _q(
                "Cash dividends are typically…",
                ("Tax-free in Pakistan", False),
                ("Taxed at source (withholding tax applied by the company)", True),
                ("Paid in shares only", False),
                ("Available only to non-filers", False),
            ),
        ],
    ),
    LessonContent(
        slug="when-not-to-invest",
        title="When NOT to be in the market",
        category="discipline",
        difficulty=1,
        body_md=(
            "Equity investing assumes you can leave money invested for "
            "**at least 5 years** without needing to liquidate during a "
            "drawdown. If you don't have that runway, equities aren't the "
            "right vehicle.\n\n"
            "**Don't invest money you'll need within 2 years.** Down payments, "
            "wedding expenses, planned tuition, business capital — all of "
            "this belongs in T-Bills or savings, not equities.\n\n"
            "**Don't invest borrowed money.** A loss combined with debt "
            "service charges compounds the damage.\n\n"
            "**Don't invest without an emergency fund.** 3-6 months of "
            "expenses in cash protects you from being forced to sell stock "
            "at the worst possible time."
        ),
        quiz=[
            _q(
                "What's the minimum reasonable horizon for equity investing?",
                ("3 weeks", False),
                ("3 months", False),
                ("5+ years", True),
                ("It doesn't matter", False),
            ),
            _q(
                "How much emergency fund should you have BEFORE investing in equities?",
                ("None — invest first", False),
                ("3-6 months of expenses in cash", True),
                ("Equal to your portfolio", False),
                ("Enough to buy one Bitcoin", False),
            ),
            _q(
                "Should you invest borrowed money in stocks?",
                ("Yes, leverage is great", False),
                ("No — losses combined with debt service can compound the damage", True),
                ("Only on Tuesdays", False),
                ("Only if you're a filer", False),
            ),
        ],
    ),
]


def quiz_to_jsonable(quiz: list[QuizQuestion]) -> list[dict]:
    """Convert quiz objects to the JSON shape stored in lessons.quiz."""
    return [
        {
            "question": q.question,
            "options": [{"text": o.text, "correct": o.correct} for o in q.options],
        }
        for q in quiz
    ]


def grade_attempt(
    quiz: list[dict], answer_indices: list[int]
) -> int:
    """Returns score in 0..100. Empty/short answers are graded as 0."""
    if not quiz:
        return 0
    if len(answer_indices) != len(quiz):
        return 0
    correct = 0
    for q, idx in zip(quiz, answer_indices):
        opts = q.get("options", [])
        if 0 <= idx < len(opts) and opts[idx].get("correct"):
            correct += 1
    return round(correct / len(quiz) * 100)
