"""Spot the same event reported by several sources.

Noa: "the same launch reaches me 3-4 times from different sources at different times,
and I have to piece together it's one thing, not three."
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from .normalize import slug

SAME_EVENT_WINDOW = timedelta(hours=12)
SAME_CHANGE_WINDOW = timedelta(days=7)

# A product name: a capitalised word, optionally followed by a version number ("Agent 4").
_PRODUCT = re.compile(r"\b([A-Z][a-zA-Z]{2,}(?:\s+\d+(?:\.\d+)?)?)\b")
_COMMON = {
    "The", "This", "That", "Now", "New", "Plan", "Plans", "Tier", "Tiers", "Every", "All",
    "Pro", "Free", "Team", "Teams", "Business", "Enterprise", "Heard",
}


def product_tokens(text: str, competitor: str) -> set[str]:
    own = slug(competitor)
    tokens = set()
    for t in _PRODUCT.findall(text):
        if t.split()[0] in _COMMON or slug(t) == own:
            continue
        if any(ch.isdigit() for ch in t) or len(t) > 4:
            tokens.add(t.lower())
    return tokens


def same_event(a_tokens: set[str], a_ts: datetime | None, b_tokens: set[str], b_ts: datetime | None) -> bool:
    if not a_tokens & b_tokens or a_ts is None or b_ts is None:
        return False
    return abs(a_ts - b_ts) <= SAME_EVENT_WINDOW
