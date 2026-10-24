"""The weekly run: capture each pricing page, diff against the last recording, decide.

  python -m brightloop live              capture now (needs Playwright), record, decide
  python -m brightloop live --offline    no network: replay the two latest recordings

Each run leaves recordings/runs/<stamp>/cases.json (the signals, in the brief's input format)
and result.json. Snapshots land in recordings/<competitor>/<stamp>/. With BASE44_APP_ID and
BASE44_TOKEN set, screenshots are uploaded to Base44 and the run's records written there; the
PNGs stay local (not committed) and the snapshot keeps their URLs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .core import run
from .core.normalize import slug
from .snapshots import diff
from .store.base44 import Base44Store
from .store.publish import publish_run

ROOT = Path(__file__).resolve().parent.parent


def _iso_week(moment: datetime, tz: str) -> str:
    year, week, _ = moment.astimezone(ZoneInfo(tz)).isocalendar()
    return f"{year}-W{week:02d}"


def _snapshots(recordings: Path, competitor: str) -> list[Path]:
    return sorted((recordings / slug(competitor)).glob("*/snapshot.json"))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def carry_homepage(prev: dict | None, cur: dict) -> str | None:
    """Keep the deck's homepage picture when this week's couldn't be taken (a bot check that
    didn't clear): reuse the last good one and say how old it is. Returns a note, or None."""
    if cur.get("homepage_screenshot"):
        cur["homepage_captured_at"] = cur.get("fetched_at")
        return None
    if not cur.get("homepage_url"):
        return None
    old_url = (prev or {}).get("homepage_screenshot_url")
    if not old_url:
        return "homepage picture unavailable this week (blocked or failed); none from earlier weeks to reuse."
    cur["homepage_screenshot_url"] = old_url
    cur["homepage_captured_at"] = prev.get("homepage_captured_at") or prev.get("fetched_at")
    return f"homepage picture unavailable this week; reusing the one from {cur['homepage_captured_at'][:10]}."


def not_checked(prev: dict) -> dict:
    """This week's stand-in when a site didn't load: last week's snapshot, unchanged and marked
    not checked. Maya: last week's screenshot marked "not checked" beats an empty slide, "because
    an empty slide just gets me questions I don't have answers to." fetched_at stays the old one,
    so every screen shows how old the pictures are, and next week compares against real data."""
    snap = dict(prev, not_checked=True)
    snap.setdefault("homepage_captured_at", prev.get("fetched_at"))
    return snap


def _relative(snapshot: dict, base: Path) -> dict:
    """Store screenshot paths relative to the repo so recordings work on any clone."""
    def rel(p):
        try:
            return str(Path(p).resolve().relative_to(base)) if p else p
        except ValueError:
            return p
    for key in ("page_screenshot", "pricing_screenshot", "homepage_screenshot"):
        snapshot[key] = rel(snapshot.get(key))
    for plan in snapshot.get("plans", []):
        plan["screenshot"] = rel(plan.get("screenshot"))
    if snapshot.get("annual"):
        snapshot["annual"]["pricing_screenshot"] = rel(snapshot["annual"].get("pricing_screenshot"))
    return snapshot


def live(config_path: Path, recordings: Path, output: Path | None, offline: bool,
         store: Base44Store | None = None) -> dict:
    cfg = _read(config_path)
    tz = cfg.get("timezone", "UTC")
    started = datetime.now(timezone.utc)
    # The weekly workflow picks the key up front and marks the run "running" under it, so the
    # app shows the run as soon as it starts; the results then land on that same record.
    stamp = os.environ.get("BRIGHTLOOP_RUN_KEY") or started.strftime("%Y-%m-%dT%H%MZ")
    signals: list[dict] = []
    errors: list[str] = []
    baselines: list[str] = []
    notes: list[str] = []  # degraded but not failed, e.g. last week's homepage picture reused
    captured: list[datetime] = []

    for comp in (c for c in cfg.get("competitors", []) if c.get("enabled")):
        name, url = comp["name"], comp["url"]
        history = _snapshots(recordings, name)
        if offline:
            if len(history) < 2:
                errors.append(f"{name}: fewer than two recordings; nothing to replay.")
                continue
            prev, cur = _read(history[-2]), _read(history[-1])
        else:
            from .sources.live import capture  # imported here so offline runs need no Playwright
            prev = _read(history[-1]) if history else None
            shots = recordings / slug(name) / stamp
            try:
                cur = _relative(capture(name, url, shots, homepage=comp.get("homepage")), ROOT)
            except Exception as exc:  # noqa: BLE001 - one site failing must not stop the others
                errors.append(f"{name}: capture failed ({type(exc).__name__}: {str(exc).splitlines()[0][:160]}).")
                if prev:
                    _write(shots / "snapshot.json", not_checked(prev))
                    notes.append(f"{name}: not checked this week; the slide shows the screenshots from "
                                 f"{prev.get('fetched_at', '')[:10]}, marked not checked.")
                continue
            note = carry_homepage(prev, cur)
            if note:
                notes.append(f"{name}: {note}")
            _write(shots / "snapshot.json", cur)
            if prev is None:
                baselines.append(name)
                continue
        found, diff_errors = diff(prev, cur)
        signals += found
        errors += diff_errors
        captured.append(datetime.fromisoformat(cur["fetched_at"].replace("Z", "+00:00")))

    # The week is the one the newest capture belongs to, so a replay keeps its original week.
    week_moment = max(captured) if captured else started
    cases = {"week": _iso_week(week_moment, tz), "timezone": tz, "brand": cfg.get("brand", {}),
             "config": {"utm_source": cfg.get("utm_source", "brightloop")}, "signals": signals}
    result = run(cases, started_at=started)
    result["run"]["errors"][:0] = errors
    result["run"]["mode"] = "replay" if offline else "live"
    if baselines:
        result["run"]["baselines"] = baselines  # first capture for these: nothing to compare yet
    if notes:
        result["run"]["notes"] = notes

    if not offline:  # a replay reproduces a recorded run; it doesn't add a new one
        run_dir = recordings / "runs" / stamp
        _write(run_dir / "cases.json", cases)
        _write(run_dir / "result.json", result)
        if store:
            names = [c["name"] for c in cfg.get("competitors", []) if c.get("enabled")]
            publish_run(store, run_dir, recordings, ROOT, names)
            result = _read(run_dir / "result.json")  # now with screenshot URLs and any publish errors
    if output:
        _write(output, result)
    return result
