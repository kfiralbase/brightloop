"""Turn one run (result, cases, snapshots) into Base44 entity records. Pure: no network.

Field names match the app's entities: Run, Change, Skipped, Snapshot.
"""

from __future__ import annotations

from ..snapshots import headline_price

# Upsert keys: re-publishing the same run updates its records instead of duplicating them.
KEYS = {
    "Run": "run_key",
    "Change": ["run_key", "item_id"],
    "Skipped": ["run_key", "signal_id"],
    "Snapshot": ["run_key", "competitor"],
}


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
            "plans": [{"name": p["name"], "price": headline_price(p["lines"]) or "", "lines": p["lines"]}
                      for p in snap.get("plans", [])],
            "page_screenshot_url": snap.get("page_screenshot_url") or "",
            "plan_screenshots": [{"name": p["name"], "url": p["screenshot_url"]}
                                 for p in snap.get("plans", []) if p.get("screenshot_url")],
        })
    return records


def _url(source: str) -> str:
    return source if source.startswith("http") or not source else f"https://{source}"
