"""
Entity extraction — companies mentioned in an article body.

Mirrors `psx_api/psx_api/news/extract.py` (see comment in sentiment.py
for why we duplicate rather than import).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Alias:
    symbol: str
    surface: str
    pattern: re.Pattern[str]


def _compile(surface: str) -> re.Pattern[str]:
    escaped = re.escape(surface.strip())
    return re.compile(rf"\b{escaped}\b", re.IGNORECASE)


def build_alias_index(rows: list[tuple[str, str]]) -> list[Alias]:
    aliases = [
        Alias(symbol=s.upper(), surface=alias.strip(), pattern=_compile(alias))
        for s, alias in rows
        if alias and alias.strip()
    ]
    aliases.sort(key=lambda a: len(a.surface), reverse=True)
    return aliases


def extract_mentions(text: str, aliases: list[Alias]) -> dict[str, int]:
    if not text or not aliases:
        return {}
    out: dict[str, int] = defaultdict(int)
    working = text
    for a in aliases:
        matches = a.pattern.findall(working)
        if matches:
            out[a.symbol] += len(matches)
            working = a.pattern.sub(" " * 4, working)
    return dict(out)


def aliases_from_securities(rows: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for symbol, name in rows:
        if not symbol:
            continue
        sym = symbol.strip().upper()
        out.append((sym, sym))
        if not name:
            continue
        out.append((sym, name.strip()))
        cleaned = re.sub(
            r"\s+(Limited|Ltd\.?|Company|Co\.?|Corporation|Corp\.?|Inc\.?|Pakistan)\.?$",
            "",
            name.strip(),
            flags=re.IGNORECASE,
        ).strip()
        if cleaned and cleaned.lower() != name.lower():
            out.append((sym, cleaned))
        first = cleaned.split()[0] if cleaned else ""
        common = {"the", "national", "pakistan", "united", "first", "general"}
        if len(first) >= 4 and first.lower() not in common and first.lower() != cleaned.lower():
            out.append((sym, first))
    return out
