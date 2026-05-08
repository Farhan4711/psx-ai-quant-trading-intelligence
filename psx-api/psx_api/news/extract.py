"""
Pure-Python entity extractor — turns an article body into a list of
(symbol, match_count) pairs.

Phase 3 v1: regex + alias matcher (~95% recall per the build plan, fast,
trivially testable). Each `Alias` carries a precompiled regex with word
boundaries to avoid matching "BANK" inside "BANKER" or "MEEZAN" inside
"MEEZANBANK". Long aliases match before short ones so "Engro Fertilizers"
takes precedence over plain "Engro".

When NER lands in Phase 4, the call sites stay the same — only the body
of `extract_mentions()` changes.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Alias:
    symbol: str
    surface: str        # "Engro Corporation Limited"
    pattern: re.Pattern[str]


def _compile(surface: str) -> re.Pattern[str]:
    """Word-boundary regex, case-insensitive, escapes regex specials."""
    escaped = re.escape(surface.strip())
    return re.compile(rf"\b{escaped}\b", re.IGNORECASE)


def build_alias_index(rows: list[tuple[str, str]]) -> list[Alias]:
    """
    `rows` is a list of (symbol, alias_string). Returns the list sorted
    by surface length descending so longer aliases match before shorter
    ones in `extract_mentions`.
    """
    aliases = [
        Alias(symbol=s.upper(), surface=alias.strip(), pattern=_compile(alias))
        for s, alias in rows
        if alias and alias.strip()
    ]
    aliases.sort(key=lambda a: len(a.surface), reverse=True)
    return aliases


def extract_mentions(text: str, aliases: list[Alias]) -> dict[str, int]:
    """
    Return a dict mapping symbol → number of mentions in `text`.

    Handles overlap by replacing each match with whitespace so longer
    aliases consume their text first and shorter ones don't double-count.
    """
    if not text or not aliases:
        return {}
    out: dict[str, int] = defaultdict(int)
    working = text
    for a in aliases:
        # findall + sub with whitespace placeholder; preserves positions
        # so subsequent regexes still see word boundaries correctly.
        matches = a.pattern.findall(working)
        if matches:
            out[a.symbol] += len(matches)
            working = a.pattern.sub(" " * 4, working)
    return dict(out)


# ── Default aliases derived from the securities table ─────────────────


def aliases_from_securities(rows: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    Given (symbol, company_name) pairs, return a list of (symbol, alias)
    candidates: the symbol itself, the full company name, and a couple of
    cleaned variants ("Engro Corporation Limited" → "Engro Corporation",
    "Engro Corp", "Engro").

    Returned as plain tuples so the caller can persist them to
    company_aliases or pass straight to build_alias_index().
    """
    out: list[tuple[str, str]] = []
    for symbol, name in rows:
        if not symbol:
            continue
        sym = symbol.strip().upper()
        out.append((sym, sym))             # the ticker itself

        if not name:
            continue
        out.append((sym, name.strip()))

        # Strip common legal suffixes
        cleaned = re.sub(
            r"\s+(Limited|Ltd\.?|Company|Co\.?|Corporation|Corp\.?|Inc\.?|Pakistan)\.?$",
            "",
            name.strip(),
            flags=re.IGNORECASE,
        ).strip()
        if cleaned and cleaned.lower() != name.lower():
            out.append((sym, cleaned))

        # First word — riskier (false positives) so we keep it when it's
        # >= 4 letters and not a common English word.
        first = cleaned.split()[0] if cleaned else ""
        common = {"the", "national", "pakistan", "united", "first", "general"}
        if (
            len(first) >= 4
            and first.lower() not in common
            and first.lower() != cleaned.lower()
        ):
            out.append((sym, first))

    return out
