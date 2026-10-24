"""Turn one run (result, cases, snapshots) into Base44 entity records. Pure: no network.

Field names match the app's entities: Run, Change, Skipped, Snapshot.
"""

from __future__ import annotations

from datetime import date

from ..snapshots import features, headline_price, plans_of

# Upsert keys: re-publishing the same run updates its records instead of duplicating them.
KEYS = {
    "Run": "run_key",
    "Change": ["run_key", "item_id"],
    "Skipped": ["run_key", "signal_id"],
    "Snapshot": ["run_key", "competitor"],
}


def week_of(week: str) -> str:
    """Monday of an ISO week ("2026-W44" → "2026-10-26"), or "" when the week is unreadable."""
    try:
        year, num = week.split("-W")
        return date.fromisocalendar(int(year), int(num), 1).isoformat()
    except (ValueError, AttributeError):
        return ""


def run_status(result: dict, snapshots: list[dict]) -> str:
    errors = result["run"].get("errors", [])
    if not errors:
        return "ok"
    return "partial" if snapshots or result["items"] or result["skipped"] else "failed"


def to_records(run_key: str, result: dict, cases: dict, snapshots: list[dict]) -> dict[str, list[dict]]:
    """Map a run to records per entity. Screenshot URLs must already be on the snapshots."""
    week = cases.get("week", "")
    run = result["run"]
    records: dict[str, list[dict]] = {
        "Run": [{
            "run_key": run_key,
            "started_at": run.get("started_at"),
            "mode": run.get("mode", "live"),
            "week": week,
            "week_of": week_of(week),  # the deck's name: "Competitor Deck Wk of <this date>"
            "status": run_status(result, snapshots),
            "items_count": len(result["items"]),
            "skipped_count": len(result["skipped"]),
            "errors": list(run.get("errors", [])),
            "baselines": list(run.get("baselines", [])),
            "cost_usd": run.get("cost_usd", 0.0),
        }],
        "Change": [],
        "Skipped": [{"run_key": run_key, "signal_id": s["id"], "reason": s["reason"]} for s in result["skipped"]],
        "Snapshot": [],
    }

    for item in result["items"]:
        lead = item["evidence"][0] if item.get("evidence") else {}
        change = item.get("change", {})
        records["Change"].append({
            "run_key": run_key,
            "item_id": item["id"],
            "week": week,
            "competitor": item.get("competitor"),
            "plan": change.get("plan") or "",
            "field": change.get("field"),
            "before": change.get("before") or "",
            "after": change.get("after") or "",
            "direction": change.get("direction") or "none",
            "confidence": item["confidence"],
            "action": item["action"],
            "why": item["why"],
            "deck_line": item.get("deck_line", ""),
            "source": _url(lead.get("source", "")),
            "source_ids": item["source_ids"],
            "screenshot_url": next((e["screenshot"] for e in item.get("evidence", [])
                                    if str(e.get("screenshot", "")).startswith("http")), ""),
            "detected_at": lead.get("ts_utc"),
        })

    for snap in snapshots:
        records["Snapshot"].append({
            "run_key": run_key,
            "competitor": snap["competitor"],
            "fetched_at": snap.get("fetched_at"),
            "url": snap.get("final_url") or snap.get("url"),
            "billing_view": snap.get("billing_view"),
            # What a viewer needs: the price and what the plan includes. CTAs, badges and the
            # raw page text stay in the repo's snapshot JSON.
            "plans": [{"name": p["name"], "price": (price := headline_price(p["lines"]) or ""),
                       "lines": features(p["lines"], price or None, p.get("controls", []))}
                      for p in plans_of(snap)],
            "page_screenshot_url": snap.get("page_screenshot_url") or "",
            # The two pictures on Maya's slide: homepage on top, pricing section below.
            "homepage_url": snap.get("homepage_url") or "",
            "homepage_screenshot_url": snap.get("homepage_screenshot_url") or "",
            # When the homepage picture is older than this run (bot check), the deck says so.
            "homepage_captured_at": snap.get("homepage_captured_at") or snap.get("fetched_at"),
            "pricing_screenshot_url": snap.get("pricing_screenshot_url") or "",
            # The site didn't load this run: these are last week's pictures, and the deck says so.
            "not_checked": bool(snap.get("not_checked")),
            "plan_screenshots": [{"name": p["name"], "url": p["screenshot_url"]}
                                 for p in plans_of(snap) if p.get("screenshot_url")],
        })
    return records


def _url(source: str) -> str:
    return source if source.startswith("http") or not source else f"https://{source}"
