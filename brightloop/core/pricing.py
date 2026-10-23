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
# "SSO moved from Pro to Business"
_TIER_MOVE = re.compile(r"\b(?:moved?|moves|now only on|restricted to)\b.{0,30}?\bfrom\s+" + _PLAN + r"\s+to\s+" + _PLAN, re.I)
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
        return self.before is not None and self.after is not None and self.field != "tier"


def _plan(text: str) -> str | None:
    m = _PLAN_IN.search(text)
    return m.group(1).title() if m else None


def _direction(before: float, after: float) -> str | None:
    return "up" if after > before else "down" if after < before else None


def _money(v: float, period: str | None) -> str:
    amount = f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"
    return amount + (f"/{'month' if period in ('mo', 'month') else period}" if period else "")


def find_change(text: str) -> Change | None:
    """Return the first pricing or packaging change stated in the text, or None."""
    plan = _plan(text)

    m = _AFTER_WAS.search(text)
    if m:
        after, period, before = _num(m.group(1)), m.group(2), _num(m.group(3))
        if before != after:
            return Change("price", plan, _money(before, period), _money(after, period),
                          _direction(before, after), m.group(0))
    m = _FROM_TO.search(text)
    if m:
        before, after, period = _num(m.group(1)), _num(m.group(2)), m.group(3)
        if before != after:
            return Change("price", plan, _money(before, period), _money(after, period),
                          _direction(before, after), m.group(0))
    m = _QTY_WAS.search(text)
    if m:
        after, unit, before = _num(m.group(1)), m.group(2).lower(), _num(m.group(3))
        if before != after:
            return Change(unit, plan, f"{before:g}", f"{after:g}", _direction(before, after), m.group(0))
    m = _QTY_FROM_TO.search(text)
    if m:
        before, after, unit = _num(m.group(1)), _num(m.group(3)), m.group(4).lower()
        if before != after:
            return Change(unit, plan, f"{before:g}", f"{after:g}", _direction(before, after), m.group(0))
    m = _TIER_MOVE.search(text)
    if m:
        return Change("tier", None, m.group(1).title(), m.group(2).title(), None, m.group(0))
    m = _RAISE_TO.search(text)
    if m:
        verb = m.group(0).split()[0].lower()
        direction = "up" if verb.startswith(("rais", "increas")) else "down"
        return Change("price", plan, None, _money(_num(m.group(1)), None), direction, m.group(0))
    m = _QUALITATIVE.search(text)
    if m:
        return Change("packaging", plan, None, None, None, m.group(0))
    return None
