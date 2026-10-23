"""The one decision path. Live runs and file runs both end up here.

Input: the cases.json shape (week, timezone, brand, config, signals).
Output: the required wrapper (built_for, items, skipped, run).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .dedup import SAME_CHANGE_WINDOW, product_tokens, same_event
from .normalize import clean_text, iso_utc, parse_ts, slug, week_bounds
from .pricing import Change, find_change
from .sources import OFFICIAL_OTHER, OFFICIAL_PRICING, THIRD_PARTY, SourceInfo, classify_source

BUILT_FOR = "maya"

# Confidence is computed from the evidence, never read from the input.
BASE_CONFIDENCE = {OFFICIAL_PRICING: 0.9, OFFICIAL_OTHER: 0.6}
NUMBERS_BONUS = 0.05       # before and after values both stated
CORROBORATION_BONUS = 0.04  # per extra independent domain reporting the same change
INJECTION_PENALTY = 0.2    # the text tried to instruct an AI; trust it less
MAX_CONFIDENCE = 0.99

_RUMOR = re.compile(
    r"\?\?|\b(heard|rumou?rs?|allegedly|reportedly|unconfirmed|word is|apparently|might be|could be)\b",
    re.IGNORECASE,
)


@dataclass
class _Candidate:
    sid: str
    competitor: str
    change: Change
    text: str  # visible text only, hidden comments already removed
    source: str
    info: SourceInfo
    ts: datetime | None
    injected: bool


@dataclass
class _Group:
    members: list[_Candidate] = field(default_factory=list)

    @property
    def first(self) -> _Candidate:
        return self.members[0]


def _change_key(c: _Candidate) -> tuple[str, ...]:
    ch = c.change
    return (slug(c.competitor), ch.field, (ch.plan or "").lower(), (ch.after or ch.quote).lower())


def _close_in_time(a: datetime | None, b: datetime | None) -> bool:
    return a is None or b is None or abs(a - b) <= SAME_CHANGE_WINDOW


def _summary(competitor: str, ch: Change) -> str:
    plan = f" {ch.plan}" if ch.plan else ""
    if ch.field == "tier":
        return f"{competitor}: moved from {ch.before} to {ch.after}"
    if ch.before and ch.after:
        unit = "" if ch.field == "price" else f" {ch.field}"
        return f"{competitor}{plan}: {ch.before}{unit} → {ch.after}{unit}"
    if ch.after:
        return f"{competitor}{plan}: price {'raised' if ch.direction == 'up' else 'cut'} to {ch.after}"
    return f"{competitor}{plan}: packaging change (\"{ch.quote}\")"


def _scrub(text: str, banned: list[str]) -> str:
    for word in banned:
        text = re.sub(re.escape(word), "[removed]", text, flags=re.IGNORECASE)
    return text


def _build_item(group: _Group, used_ids: set[str], week: str, utm_source: str, banned: list[str]) -> dict:
    # Lead with the pricing page, then the earliest report.
    members = sorted(group.members, key=lambda c: (c.info.tier != OFFICIAL_PRICING, c.ts is None, iso_utc(c.ts) or ""))
    lead = members[0]
    ch, comp = lead.change, lead.competitor
    tier = OFFICIAL_PRICING if any(m.info.tier == OFFICIAL_PRICING for m in members) else OFFICIAL_OTHER
    domains = {m.info.domain for m in members if m.info.domain}

    confidence = BASE_CONFIDENCE[tier]
    if ch.has_numbers:
        confidence += NUMBERS_BONUS
    confidence += CORROBORATION_BONUS * max(0, len(domains) - 1)
    if any(m.injected for m in members):
        confidence -= INJECTION_PENALTY
    confidence = round(min(MAX_CONFIDENCE, max(0.0, confidence)), 2)

    summary = _summary(comp, ch)
    if tier == OFFICIAL_PRICING:
        action = (f"Add a slide to Monday's deck: {summary}, with a screenshot of {lead.source}. "
                  f"Then update the Brightloop vs {comp} comparison page.")
        if ch.direction == "up":
            action += (f" Price went up: check whether Brightloop is now cheaper on this plan; "
                       f"if it is, that's a 'cheaper than {comp}' angle for Daniel.")
        elif ch.direction == "down":
            action += f" Price went down: re-check any 'cheaper than {comp}' claims in our ads and pages."
    else:
        action = (f"Confirm on {comp}'s pricing page before it goes in the deck: {summary} "
                  f"(announced on {lead.source}, not yet seen on the pricing page).")

    seen_on = ", ".join(dict.fromkeys(m.source for m in members if m.source)) or "an unnamed source"
    why = f"{summary}, stated on {seen_on} ({iso_utc(lead.ts) or 'time not given'})."
    if tier == OFFICIAL_PRICING:
        why += " Source is the competitor's own pricing page, with the numbers next to it."
    else:
        why += " Official channel but not the pricing page, so confidence stays below the deck bar."
    if len(domains) > 1:
        why += f" {len(domains)} independent sources report the same change."
    if any(m.injected for m in members):
        why += " One source contained hidden instructions aimed at AI systems; they were ignored."

    base_id = f"chg-{slug(comp)}-{slug(ch.plan or 'all')}-{slug(ch.field)}-{slug(ch.after or 'change')}"
    item_id, n = base_id, 2
    while item_id in used_ids:
        item_id, n = f"{base_id}-{n}", n + 1
    used_ids.add(item_id)

    campaign = f"{week.lower()}-{slug(comp)}-pricing" if week else f"{slug(comp)}-pricing"
    return {
        "id": item_id,
        "source_ids": [m.sid for m in members],
        "confidence": confidence,
        "action": _scrub(action, banned),
        "why": _scrub(why, banned),
        "competitor": comp,
        "change": {"field": ch.field, "plan": ch.plan, "before": ch.before, "after": ch.after,
                   "direction": ch.direction},
        "evidence": [{"source_id": m.sid, "source": m.source, "ts_utc": iso_utc(m.ts),
                      "quote": m.text, "source_tier": m.info.tier} for m in members],
        "cta": {"label": f"Review the {comp} pricing change",
                "utm": f"utm_source={utm_source}&utm_medium=pricing_deck&utm_campaign={campaign}"},
    }


def run(payload: object, *, started_at: datetime) -> dict:
    errors: list[str] = []
    skipped: list[dict] = []
    out = {"built_for": BUILT_FOR, "items": [], "skipped": skipped,
           "run": {"started_at": started_at.isoformat(timespec="seconds"), "cost_usd": 0.0, "errors": errors}}

    if not isinstance(payload, dict):
        errors.append("Input is not a JSON object; nothing to process.")
        return out

    tz = payload.get("timezone") if isinstance(payload.get("timezone"), str) else "UTC"
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        errors.append(f"Unknown timezone {tz!r}; using UTC.")
        tz = "UTC"

    week = payload.get("week") if isinstance(payload.get("week"), str) else ""
    bounds = week_bounds(week, tz)
    if week and bounds is None:
        errors.append(f"Unreadable week {week!r}; no week filter applied.")

    brand = payload.get("brand") if isinstance(payload.get("brand"), dict) else {}
    banned = [w for w in brand.get("banned_words", []) if isinstance(w, str) and w.strip()]
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    utm_source = config.get("utm_source") if isinstance(config.get("utm_source"), str) else "brightloop"

    signals = payload.get("signals")
    if not isinstance(signals, list):
        errors.append("Input has no 'signals' list; nothing to process.")
        return out

    def skip(sid: str, reason: str, injected: bool = False) -> None:
        if injected:
            reason += " It also contained hidden instructions aimed at AI systems; ignored."
        skipped.append({"id": sid, "reason": _scrub(reason, banned)})

    seen: list[str] = []
    launches: list[tuple[str, str, set[str], datetime | None]] = []
    candidates: list[_Candidate] = []

    for index, s in enumerate(signals):
        if not isinstance(s, dict):
            errors.append(f"signals[{index}] is not an object; it has no id to report.")
            continue
        raw_id = s.get("id")
        if isinstance(raw_id, (int, float)) and not isinstance(raw_id, bool):
            raw_id = str(raw_id)
        if not isinstance(raw_id, str) or not raw_id.strip():
            errors.append(f"signals[{index}] has no id; it can't be placed in items or skipped.")
            continue
        sid = raw_id
        if sid in seen:
            errors.append(f"Duplicate id {sid!r} at signals[{index}]; only the first one was used.")
            continue
        seen.append(sid)

        kind = str(s.get("type") or "").strip().lower()
        competitor = str(s.get("competitor") or "").strip() or "Unknown competitor"
        text, injected = clean_text(s.get("text"))
        ts = parse_ts(s.get("ts"), tz)
        if s.get("ts") and ts is None:
            errors.append(f"{sid}: unreadable timestamp {s.get('ts')!r}.")

        if kind == "ad":
            skip(sid, "Ad, not a pricing-page change: out of scope for the pricing deck. "
                      "predicted_ctr is a model score and is not used for anything.", injected)
            continue
        if kind not in ("pricing", "launch"):
            skip(sid, f"Unknown signal type {kind or '(none)'!r}; only pricing changes go in the deck.", injected)
            continue
        if not text:
            skip(sid, "No readable text, so no change can be confirmed.", injected)
            continue

        source = s.get("source") if isinstance(s.get("source"), str) else ""
        info = classify_source(source, competitor)
        change = find_change(text)

        if _RUMOR.search(text):
            who = " from an anonymous source" if info.unvetted else ""
            skip(sid, f"Rumor{who} (speculative wording), not a confirmed change.", injected)
        elif change is None and kind == "launch":
            tokens = product_tokens(text, competitor)
            twin = next((other for other, other_comp, toks, other_ts in launches
                         if other_comp == slug(competitor) and same_event(tokens, ts, toks, other_ts)), None)
            launches.append((sid, slug(competitor), tokens, ts))
            reason = "Feature launch with no price change: product's area, not the pricing deck."
            if twin:
                reason += f" Same event as {twin}, reported by another source."
            skip(sid, reason, injected)
        elif change is None:
            skip(sid, "No change stated. A price with no previous value isn't a change.", injected)
        elif info.tier == THIRD_PARTY:
            where = ("a sponsored post" if info.paid else
                     "a placeholder domain" if info.placeholder else
                     info.domain or "an unknown source")
            skip(sid, f"Unverified pricing claim from {where}, not {competitor}'s own pricing page. "
                      f"Check the pricing page before it goes anywhere.", injected)
        elif bounds and ts and not (bounds[0] <= ts < bounds[1]):
            skip(sid, f"Outside {week} ({tz}).", injected)
        else:
            candidates.append(_Candidate(sid, competitor, change, text, source, info, ts, injected))

    groups: list[_Group] = []
    for c in candidates:
        home = next((g for g in groups
                     if _change_key(g.first) == _change_key(c) and _close_in_time(g.first.ts, c.ts)), None)
        if home:
            home.members.append(c)
        else:
            groups.append(_Group([c]))

    used_ids: set[str] = set()
    items = [_build_item(g, used_ids, week, utm_source, banned) for g in groups]
    items.sort(key=lambda i: (-i["confidence"], i["id"]))
    out["items"] = items

    placed = [sid for i in items for sid in i["source_ids"]] + [k["id"] for k in skipped]
    if sorted(placed) != sorted(seen):
        errors.append("Internal check failed: not every input id was placed exactly once.")
    return out
