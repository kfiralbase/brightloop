"""Compare two pricing-page snapshots and describe what moved, as cases.json signals.

Pure: snapshots in, signals out. The signal text is plain English that the core reads with
the same rules it applies to any input file, so live runs and file runs share one decision path.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .core.normalize import slug

_MONEY = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
_HEADLINE = re.compile(r"(\$\s?\d[\d,]*(?:\.\d+)?)(?:\s*\*)?(?:\s*(?:/|per)\s*(month|mo|year|yr|member|seat|user))?", re.I)
_NON_NUMERIC_PRICE = re.compile(r"^(custom|platform fee|contact sales|free)$", re.I)
_DIGITS = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Calls to action, badges and footnotes: not part of what a plan includes.
_NOISE = re.compile(
    r"^(get started|get \w+|start( a)? \w+|start free|try now|upgrade( to \w+)?|book a demo|contact sales|"
    r"most popular|popular|recommended|best value|\*|/\s*month|/month|billed \w+|save .*|"
    r"everything in \w+(, plus.*| plus:?)|all \w+ features)$",
    re.I,
)
MAX_FEATURE_LEN = 90

# Names of steps on a pricing ladder. A card with another name counts as a plan only if it
# shows a $ price: that keeps "Lovable for campus" (contact sales) out and real plans in.
PLAN_NAMES = [
    "Free", "Starter", "Hobby", "Basic", "Core", "Plus", "Pro", "Premium", "Max", "Ultra",
    "Team", "Teams", "Business", "Scale", "Growth", "Enterprise",
]
_PLAN_SET = {n.lower() for n in PLAN_NAMES}


def is_plan(name: str, lines: list[str]) -> bool:
    return name.strip().lower() in _PLAN_SET or any(_MONEY.search(line) for line in lines)


def plans_of(snapshot: dict) -> list[dict]:
    """The snapshot's plans, without side programs (also drops them from older recordings)."""
    return [p for p in snapshot.get("plans", []) if is_plan(p["name"], p["lines"])]


def source_label(url: str) -> str:
    u = urlparse(url)
    return (u.netloc.removeprefix("www.") + u.path).rstrip("/")


def headline_price(lines: list[str]) -> str | None:
    """The plan's own price: the first amount on the card, with its period if it has one."""
    text = " ".join(lines)
    m = _HEADLINE.search(text)
    if m:
        amount = m.group(1).replace(" ", "")
        period = m.group(2)
        if period in ("mo",):
            period = "month"
        return f"{amount}/{period.lower()}" if period else amount
    for line in lines[1:6]:
        if _NON_NUMERIC_PRICE.match(line):
            return line.title()
    return None


def features(lines: list[str], price: str | None) -> list[str]:
    """Lines that describe what the plan includes, without the name, price, CTAs or blurbs."""
    out = []
    for i, line in enumerate(lines):
        if i == 0 or _NOISE.match(line) or line == "*" or line.lower() in _PLAN_SET:
            continue  # the name can sit below a badge, so it isn't always the first line
        if price and line.replace(" ", "").lower() in (price.replace(" ", "").lower(), price.split("/")[0].lower()):
            continue
        if _HEADLINE.fullmatch(line.strip()):
            continue
        if len(line) > MAX_FEATURE_LEN or (line.endswith(".") and len(line.split()) > 5):
            continue  # marketing sentence, not an entitlement
        out.append(line)
    return out


def _shape(line: str) -> str:
    return _DIGITS.sub("#", line.lower())


def diff(prev: dict, cur: dict) -> tuple[list[dict], list[str]]:
    """Return (signals, errors) describing what changed from prev to cur for one competitor."""
    comp = cur.get("competitor") or prev.get("competitor") or "Unknown"
    errors: list[str] = []
    prev_plans = {p["name"]: p for p in plans_of(prev)}
    cur_plans = {p["name"]: p for p in plans_of(cur)}

    if not cur_plans:
        return [], [f"{comp}: no plans found on the page this time; nothing compared."]
    lost = [n for n in prev_plans if n not in cur_plans]
    if prev_plans and len(lost) * 2 > len(prev_plans):
        return [], [f"{comp}: {len(lost)} of {len(prev_plans)} plans not found this time; "
                    f"treated as an extraction problem, not removals."]
    compare_prices = prev.get("billing_view") == cur.get("billing_view")
    if not compare_prices:
        errors.append(f"{comp}: billing view changed ({prev.get('billing_view')} → "
                      f"{cur.get('billing_view')}); prices not compared this time.")

    texts: list[tuple[str, str | None]] = []  # (text, screenshot)

    for name in lost:
        texts.append((f"{name} plan removed from the pricing page.", None))
    for name, plan in cur_plans.items():
        if name not in prev_plans and prev_plans:
            price = headline_price(plan["lines"])
            texts.append((f"New {name} plan added to the pricing page" + (f" at {price}." if price else "."),
                          plan.get("screenshot")))

    removed: dict[str, list[str]] = {}
    added: dict[str, list[str]] = {}
    for name in cur_plans.keys() & prev_plans.keys():
        before, after = prev_plans[name], cur_plans[name]
        shot = after.get("screenshot")
        old_price, new_price = headline_price(before["lines"]), headline_price(after["lines"])
        if compare_prices and old_price and new_price and old_price != new_price:
            if _MONEY.match(old_price) and _MONEY.match(new_price):
                texts.append((f"{name} plan shown at {new_price} (was {old_price} last week).", shot))
            else:
                texts.append((f"{name} plan: '{old_price}' is now '{new_price}'.", shot))

        old_f, new_f = features(before["lines"], old_price), features(after["lines"], new_price)
        gone = [f for f in old_f if f not in new_f]
        came = [f for f in new_f if f not in old_f]
        # Same line with different numbers: "100 monthly credits" → "50 monthly credits".
        for g in list(gone):
            twin = next((c for c in came if _shape(c) == _shape(g)), None)
            if twin:
                gone.remove(g)
                came.remove(twin)
                texts.append((f"{name} plan: '{g}' is now '{twin}'.", shot))
        removed[name], added[name] = gone, came

    # A line that left one plan and appeared in another moved tiers.
    for src, lines in removed.items():
        for line in list(lines):
            dst = next((d for d, adds in added.items() if d != src and line in adds), None)
            if dst:
                lines.remove(line)
                added[dst].remove(line)
                texts.append((f"'{line}' moved from {src} to {dst}.", cur_plans[dst].get("screenshot")))
    for name, lines in removed.items():
        texts += [(f"'{line}' removed from the {name} plan.", cur_plans[name].get("screenshot")) for line in lines]
    for name, lines in added.items():
        texts += [(f"'{line}' added to the {name} plan.", cur_plans[name].get("screenshot")) for line in lines]

    source = source_label(cur.get("final_url") or cur.get("url") or "")
    signals = []
    for n, (text, shot) in enumerate(texts, start=1):
        sig = {"id": f"live-{slug(comp)}-{cur.get('fetched_at', '')[:10]}-{n}", "type": "pricing",
               "competitor": comp, "source": source, "ts": cur.get("fetched_at"), "text": text}
        if shot:
            sig["screenshot"] = shot
        signals.append(sig)
    return signals, errors
