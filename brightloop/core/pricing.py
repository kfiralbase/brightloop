"""Find a pricing or packaging change in a line of text, and pull out its numbers.

Maya: "price, plan limits, free tier, seats, credits — if it's on their pricing page
and it moved, I flag it." Numbers come only from the text itself. Nothing is estimated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MONEY = r"\$\s?(\d[\d,]*(?:\.\d+)?)"
_QTY = r"(\d[\d,]*(?:\.\d+)?)\s*(?:k\b)?"
_UNITS = (
    r"(credits?|messages?|seats?|users?|requests?|projects?|tokens?|"
    r"deployments?|builds?|apps?|minutes?|hours?|GB|members?)"
)
_PLAN = (
    r"(Free|Starter|Core|Pro|Plus|Premium|Teams?|Business|Enterprise|Scale|Hobby|Basic|"
    r"Launch|Growth|Ultra|Max)"
)
_PERIOD = r"(?:\s*(?:/|per|a)\s*(month|mo|year|yr|seat|user))?"

# "$25/month (was $20 last week)"
_AFTER_WAS = re.compile(_MONEY + _PERIOD + r"[^$]{0,40}?\(?\b(?:was|previously|up from|down from)\s+" + _MONEY, re.I)
# "from $20 to $25", "$20 → $25", "$20 -> $25"
_FROM_TO = re.compile(r"(?:from\s+)?" + _MONEY + r"\s*(?:→|->|=>|\bto\b)\s*" + _MONEY + _PERIOD, re.I)
# "100 credits (was 200)", "from 200 to 100 credits", "200 → 100 credits"
_QTY_WAS = re.compile(_QTY + r"\s*" + _UNITS + r"[^\d]{0,30}?\(?\b(?:was|previously|up from|down from)\s+" + _QTY, re.I)
_QTY_FROM_TO = re.compile(r"\bfrom\s+" + _QTY + r"\s*(?:" + _UNITS + r"\s*)?(?:→|->|\bto\b)\s*" + _QTY + r"\s*" + _UNITS, re.I)
# "Free tier: 5→3 projects" (Maya's own example), "200 -> 100 credits"
_QTY_ARROW = re.compile(r"(?<![\d$.,])(\d[\d,]*(?:\.\d+)?)\s*(?:→|->|=>)\s*(\d[\d,]*(?:\.\d+)?)\s*" + _UNITS, re.I)
# "Credits on Pro cut from 100 to 50"
_UNIT_FROM_TO = re.compile(r"\b" + _UNITS + r"\b[^\d$]{0,40}?\bfrom\s+" + _QTY + r"\s*(?:→|->|\bto\b)\s*" + _QTY, re.I)
_CURRENCY = re.compile(r"[€£₪]")
_DOLLAR = re.compile(r"\$").search("$")
# "SSO moved from Pro to Business"
_TIER_MOVE = re.compile(r"(?:'[^']{1,90}'\s+)?\b(?:moved?|moves|now only on|restricted to)\b.{0,120}?\bfrom\s+"
                        + _PLAN + r"\s+to\s+" + _PLAN, re.I)
# Phrasings written by the snapshot diff (brightloop/snapshots.py)
_LINE_EDIT = re.compile(r"\b([\w][\w ]{0,40}?) plan: '(.+?)' is now '(.+?)'", re.I)
_FEATURE_EDIT = re.compile(r"'(.+?)' (added to|removed from) the ([\w][\w ]{0,40}?) plan\b", re.I)
_UNIT_IN = re.compile(r"\b" + _UNITS + r"\b", re.I)
# Free tier / plan changes with no number
_QUALITATIVE = re.compile(
    r"\b(free (?:tier|plan)\b.{0,40}\b(?:removed|discontinued|ended|cut|reduced|eliminated|"
    r"no longer|added|introduced|now includes|expanded)|no longer (?:free|offers? a free)|"
    r"(?:now|is now) free\b|free forever|price (?:increase|hike|cut|drop)|"
    r"(?:raised|raises|increased|increases|cut|cuts|dropped|drops|lowered|lowers|reduced|reduces)"
    r"\s+(?:its |their |the )?(?:prices?|pricing)|per[- ]seat pricing|"
    r"(?:plan|tier) (?:removed|discontinued|retired|renamed|added))",
    re.I,
)
_RAISE_TO = re.compile(r"\b(?:raised|raises|increased|increases|cut|cuts|dropped|drops|lowered|lowers|reduced|reduces)\b[^$]{0,40}?\bto\s+" + _MONEY, re.I)
_PLAN_IN = re.compile(r"\b" + _PLAN + r"\b(?:\s+(?:plan|tier))?", re.I)


def _num(raw: str) -> float:
    return float(raw.replace(",", ""))


@dataclass(frozen=True)
class Change:
    field: str            # "price", a unit like "credits", "tier", or "packaging"
    plan: str | None
    before: str | None
    after: str | None
    direction: str | None  # "up", "down" or None
    quote: str            # the exact text the change was read from

    @property
    def has_numbers(self) -> bool:
        return (self.before is not None and self.after is not None and self.field not in ("tier", "packaging")
                and bool(re.search(r"\d", self.before)) and bool(re.search(r"\d", self.after)))


def _plan(text: str) -> str | None:
    m = _PLAN_IN.search(text)
    return m.group(1).title() if m else None


def _direction(before: float, after: float) -> str | None:
    return "up" if after > before else "down" if after < before else None


def _money(v: float, period: str | None, currency: str = "$") -> str:
    amount = f"{currency}{v:,.0f}" if v == int(v) else f"{currency}{v:,.2f}"
    return amount + (f"/{'month' if period in ('mo', 'month') else period}" if period else "")


def find_change(text: str) -> Change | None:
    """Return the first pricing or packaging change stated in the text, or None."""
    m = _LINE_EDIT.search(text)
    if m:
        plan_name, before, after = m.group(1).strip().title(), m.group(2), m.group(3)
        if re.search(r"\d", before) and re.search(r"\d", after):
            unit = _UNIT_IN.search(after)
            nums_b, nums_a = re.findall(r"\d[\d,.]*", before), re.findall(r"\d[\d,.]*", after)
            direction = (_direction(_num(nums_b[0]), _num(nums_a[0]))
                         if len(nums_b) == len(nums_a) == 1 else None)
            return Change(unit.group(1).lower() if unit else "limit", plan_name, before, after, direction, m.group(0))
        return Change("packaging", plan_name, before, after, None, m.group(0))
    m = _FEATURE_EDIT.search(text)
    if m:
        line, verb, plan_name = m.group(1), m.group(2).lower(), m.group(3).strip().title()
        before, after = (None, line) if verb.startswith("added") else (line, None)
        return Change("packaging", plan_name, before, after, None, m.group(0))

    plan = _plan(text)
    # Other currencies read like dollars and keep their own symbol. Each symbol is one character,
    # so positions in the normalized text match the original and quotes keep the real symbol.
    original = text
    currency = (_CURRENCY.search(text) or _DOLLAR).group(0)
    text = _CURRENCY.sub("$", text)

    def quote(m: re.Match) -> str:
        return original[m.start():m.end()]

    m = _AFTER_WAS.search(text)
    if m:
        after, period, before = _num(m.group(1)), m.group(2), _num(m.group(3))
        if before != after:
            return Change("price", plan, _money(before, period, currency), _money(after, period, currency),
                          _direction(before, after), quote(m))
    m = _FROM_TO.search(text)
    if m:
        before, after, period = _num(m.group(1)), _num(m.group(2)), m.group(3)
        if before != after:
            return Change("price", plan, _money(before, period, currency), _money(after, period, currency),
                          _direction(before, after), quote(m))
    m = _QTY_WAS.search(text)
    if m:
        after, unit, before = _num(m.group(1)), m.group(2).lower(), _num(m.group(3))
        if before != after:
            return Change(unit, plan, f"{before:g}", f"{after:g}", _direction(before, after), quote(m))
    m = _QTY_FROM_TO.search(text)
    if m:
        before, after, unit = _num(m.group(1)), _num(m.group(3)), m.group(4).lower()
        if before != after:
            return Change(unit, plan, f"{before:g}", f"{after:g}", _direction(before, after), quote(m))
    m = _QTY_ARROW.search(text)
    if m:
        before, after, unit = _num(m.group(1)), _num(m.group(2)), m.group(3).lower()
        if before != after:
            return Change(unit, plan, f"{before:g}", f"{after:g}", _direction(before, after), quote(m))
    m = _UNIT_FROM_TO.search(text)
    if m:
        unit, before, after = m.group(1).lower(), _num(m.group(2)), _num(m.group(3))
        if before != after:
            return Change(unit, plan, f"{before:g}", f"{after:g}", _direction(before, after), quote(m))
    m = _TIER_MOVE.search(text)
    if m:
        return Change("tier", None, m.group(1).title(), m.group(2).title(), None, quote(m))
    m = _RAISE_TO.search(text)
    if m:
        verb = m.group(0).split()[0].lower()
        direction = "up" if verb.startswith(("rais", "increas")) else "down"
        return Change("price", plan, None, _money(_num(m.group(1)), None, currency), direction, quote(m))
    m = _QUALITATIVE.search(text)
    if m:
        return Change("packaging", plan, None, None, None, quote(m))
    return None
