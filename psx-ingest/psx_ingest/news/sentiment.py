"""
Lexicon sentiment scorer + event-type classifier.

Mirrors `psx_api/psx_api/news/sentiment.py` so the ingest worker can
score articles at write time without importing psx-api. The two
implementations MUST stay byte-identical — both return rows that
go into `article_sentiment` and the model_version string is what
tells consumers which scorer wrote each row. When Phase 8 (psx-shared)
lands we'll fold these into one package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


MODEL_VERSION_LEXICON = "lexicon-v0.1.0"

_POSITIVE_WORDS = frozenset(
    [
        "profit", "profits", "profitable", "growth", "gain", "gains", "gained",
        "surged", "rally", "rallied", "outperform", "beat", "beats", "beating",
        "record", "milestone", "expansion", "expanded", "strong", "robust",
        "upgrade", "upgraded", "approve", "approval", "approved", "dividend",
        "bonus", "buyback", "exceed", "exceeded", "boost", "boosted", "improve",
        "improved", "improvement", "ease", "eased", "favourable", "favorable",
        "positive", "promising", "successful", "win", "won", "secure", "secured",
    ]
)

_NEGATIVE_WORDS = frozenset(
    [
        "loss", "losses", "decline", "declined", "fall", "fell", "plunge",
        "plunged", "crash", "crashed", "bearish", "miss", "missed", "missing",
        "underperform", "downgrade", "downgraded", "weak", "weakened",
        "concern", "concerns", "worrying", "investigation", "fraud", "scandal",
        "lawsuit", "fine", "fined", "penalty", "penalties", "default",
        "defaulted", "bankruptcy", "shutdown", "layoff", "layoffs", "fired",
        "resign", "resigned", "warning", "warnings", "risk", "risks", "halt",
        "halted", "suspend", "suspended", "delay", "delayed", "negative",
        "deteriorate", "deteriorated", "tumble", "tumbled", "slump", "slumped",
    ]
)

_NEGATORS = frozenset({"not", "no", "never", "n't", "without", "fails", "failed"})

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


@dataclass(frozen=True)
class SentimentResult:
    polarity: float
    event_type: str
    model_version: str


def score_lexicon(text: str) -> SentimentResult:
    if not text:
        return SentimentResult(0.0, "general", MODEL_VERSION_LEXICON)

    tokens = re.findall(r"[A-Za-z']+", text.lower())
    pos = 0
    neg = 0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _NEGATORS:
            for j in range(i + 1, min(i + 4, len(tokens))):
                w = tokens[j]
                if w in _POSITIVE_WORDS:
                    neg += 1
                    i = j
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
