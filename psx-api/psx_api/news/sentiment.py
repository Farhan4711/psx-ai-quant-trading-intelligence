"""
Sentiment scoring.

Phase 3 v1 ships a lexicon-based fallback (`score_lexicon`) — fast,
deterministic, no PyTorch dependency, ~70% accuracy on Loughran-McDonald
financial benchmark per published lit. Real FinBERT inference (Step 51
Tier 1) and LLM extraction (Tier 2) are gated behind capability
detection: if the optional `transformers` import is available the
service can swap in `score_finbert`, otherwise the lexicon scorer is
used and the API stays identical.

Output:
  - polarity      ∈ [-1, +1]
  - event_type    one of: earnings, guidance, regulatory, macro, mna,
                  leadership, scandal, general
  - model_version string for the article_sentiment row
"""

from __future__ import annotations

import re
from dataclasses import dataclass


MODEL_VERSION_LEXICON = "lexicon-v0.1.0"
MODEL_VERSION_FINBERT = "finbert-prosus-v1"


# ── Lexicons ────────────────────────────────────────────────────────────


# Adapted from Loughran-McDonald financial sentiment lexicon (subset
# focused on Pakistani business-news vocabulary). Each list is small
# enough to be reviewable; the important thing is that the *set is
# stable* — the sentiment of a saved article shouldn't drift when we
# edit the lexicon later. Persisting the model_version string is what
# preserves the contract.

_POSITIVE_WORDS = frozenset(
    [
        "profit",
        "profits",
        "profitable",
        "growth",
        "gain",
        "gains",
        "gained",
        "surged",
        "rally",
        "rallied",
        "outperform",
        "beat",
        "beats",
        "beating",
        "record",
        "milestone",
        "expansion",
        "expanded",
        "strong",
        "robust",
        "upgrade",
        "upgraded",
        "approve",
        "approval",
        "approved",
        "dividend",
        "bonus",
        "buyback",
        "exceed",
        "exceeded",
        "boost",
        "boosted",
        "improve",
        "improved",
        "improvement",
        "ease",
        "eased",
        "favourable",
        "favorable",
        "positive",
        "promising",
        "successful",
        "win",
        "won",
        "secure",
        "secured",
    ]
)

_NEGATIVE_WORDS = frozenset(
    [
        "loss",
        "losses",
        "decline",
        "declined",
        "fall",
        "fell",
        "plunge",
        "plunged",
        "crash",
        "crashed",
        "bearish",
        "miss",
        "missed",
        "missing",
        "underperform",
        "downgrade",
        "downgraded",
        "weak",
        "weakened",
        "concern",
        "concerns",
        "worrying",
        "investigation",
        "fraud",
        "scandal",
        "lawsuit",
        "fine",
        "fined",
        "penalty",
        "penalties",
        "default",
        "defaulted",
        "bankruptcy",
        "shutdown",
        "layoff",
        "layoffs",
        "fired",
        "resign",
        "resigned",
        "warning",
        "warnings",
        "risk",
        "risks",
        "halt",
        "halted",
        "suspend",
        "suspended",
        "delay",
        "delayed",
        "negative",
        "deteriorate",
        "deteriorated",
        "tumble",
        "tumbled",
        "slump",
        "slumped",
    ]
)

# Negation flips the sentiment of the next 3 tokens
_NEGATORS = frozenset({"not", "no", "never", "n't", "without", "fails", "failed"})


# ── Event-type heuristics ─────────────────────────────────────────────


_EVENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("earnings", re.compile(r"\b(earnings|quarterly results|profit after tax|revenue|EPS|bottom[- ]line)\b", re.I)),
    ("guidance", re.compile(r"\b(guidance|forecast|outlook)\b", re.I)),
    ("mna", re.compile(r"\b(merger|acquisition|takeover|buyout|acquir(?:e|ed|ing)|m&a)\b", re.I)),
    ("regulatory", re.compile(r"\b(SECP|SBP|FBR|regulator|regulatory|policy rate|tariff|tax(?: on)?|circular)\b", re.I)),
    ("leadership", re.compile(r"\b(CEO|chairman|chairperson|chief executive|director|board|resign(?:ed|ation)?|appointed)\b", re.I)),
    ("scandal", re.compile(r"\b(fraud|scandal|investigation|probe|insider trading|manipulation)\b", re.I)),
    ("macro", re.compile(r"\b(KIBOR|inflation|CPI|PKR/USD|rupee|IMF|fiscal deficit|current account)\b", re.I)),
]


def _classify_event(text: str) -> str:
    for label, pattern in _EVENT_PATTERNS:
        if pattern.search(text):
            return label
    return "general"


# ── Public API ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SentimentResult:
    polarity: float           # in [-1, +1]
    event_type: str
    model_version: str


def score_lexicon(text: str) -> SentimentResult:
    """
    Token-level positive/negative count with negation handling.

    Polarity = (pos - neg) / max(pos + neg, 1), clamped to [-1, +1].
    """
    if not text:
        return SentimentResult(polarity=0.0, event_type="general", model_version=MODEL_VERSION_LEXICON)

    tokens = re.findall(r"[A-Za-z']+", text.lower())
    pos = 0
    neg = 0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _NEGATORS:
            # Look 1..3 tokens ahead and flip
            for j in range(i + 1, min(i + 4, len(tokens))):
                w = tokens[j]
                if w in _POSITIVE_WORDS:
                    neg += 1
                    i = j  # skip past the flipped word
                    break
                if w in _NEGATIVE_WORDS:
                    pos += 1
                    i = j
                    break
        elif tok in _POSITIVE_WORDS:
            pos += 1
        elif tok in _NEGATIVE_WORDS:
            neg += 1
        i += 1

    denom = max(pos + neg, 1)
    polarity = (pos - neg) / denom
    return SentimentResult(
        polarity=round(max(-1.0, min(1.0, polarity)), 3),
        event_type=_classify_event(text),
        model_version=MODEL_VERSION_LEXICON,
    )


def score(text: str) -> SentimentResult:
    """
    Production entry point — picks the best available scorer.

    For now always returns the lexicon scorer; once optional `transformers`
    + the FinBERT model is available, this function detects + delegates.
    """
    return score_lexicon(text)
