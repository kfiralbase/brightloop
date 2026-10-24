"""Publish one recorded run to Base44: upload its screenshots, then upsert its records.

Failures are returned as error strings, never raised: a run that decided correctly but
couldn't publish still has its result.json and its recording in the repo.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..core.normalize import slug
from .base44 import Base44Error, Base44Store
from .records import KEYS, to_records

PUBLISH_PREFIX = "Publish: "


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def publish_run(store: Base44Store, run_dir: Path, recordings: Path, root: Path, competitors: list[str]) -> list[str]:
    stamp = run_dir.name
    cases, result = _read(run_dir / "cases.json"), _read(run_dir / "result.json")
    errors: list[str] = []
    urls: dict[str, str] = {}  # local screenshot path → uploaded URL

    def upload(local: str | None) -> str | None:
        if not local:
            return None
        if local in urls:
            return urls[local]
        path = (root / local) if not Path(local).is_absolute() else Path(local)
        if not path.exists():
            return None
        try:
            urls[local] = store.upload(path)
        except Base44Error as exc:
            errors.append(f"Screenshot upload failed: {exc}")
            return None
        return urls[local]

    snapshots = []
    for name in competitors:
        snap_path = recordings / slug(name) / stamp / "snapshot.json"
        if not snap_path.exists():
            continue
        snap = _read(snap_path)
        gained = False
        for key in ("page_screenshot", "pricing_screenshot", "homepage_screenshot"):
            if not snap.get(f"{key}_url") and (url := upload(snap.get(key))):
                snap[f"{key}_url"], gained = url, True
        for plan in snap.get("plans", []):
            if not plan.get("screenshot_url") and (url := upload(plan.get("screenshot"))):
                plan["screenshot_url"], gained = url, True
            if plan.get("screenshot_url") and plan.get("screenshot"):
                urls.setdefault(plan["screenshot"], plan["screenshot_url"])
        if gained:
            _write(snap_path, snap)  # keep the URLs with the recording
        snapshots.append(snap)

    for item in result["items"]:
        for ev in item.get("evidence", []):
            if ev.get("screenshot") in urls:
                ev["screenshot"] = urls[ev["screenshot"]]

    records = to_records(stamp, result, cases, snapshots)
    for entity in ("Snapshot", "Change", "Skipped"):
        if records[entity]:
            try:
                store.upsert(entity, KEYS[entity], records[entity])
            except Base44Error as exc:
                errors.append(f"Writing {entity} records failed: {exc}")

    # The Run record goes last and carries this publish's errors, so the app shows them.
    # Errors from an earlier publish attempt are replaced, not piled up.
    decided = [e for e in result["run"].get("errors", []) if not e.startswith(PUBLISH_PREFIX)]
    result["run"]["errors"] = decided + [PUBLISH_PREFIX + e for e in errors]
    run_record = to_records(stamp, result, cases, snapshots)["Run"]
    try:
        store.upsert("Run", KEYS["Run"], run_record)
    except Base44Error as exc:
        errors.append(f"Writing the Run record failed: {exc}")
        result["run"]["errors"].append(PUBLISH_PREFIX + errors[-1])
    _write(run_dir / "result.json", result)
    return errors
