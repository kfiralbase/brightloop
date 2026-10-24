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
    return snapshot


def live(config_path: Path, recordings: Path, output: Path | None, offline: bool,
         store: Base44Store | None = None) -> dict:
    cfg = _read(config_path)
    tz = cfg.get("timezone", "UTC")
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y-%m-%dT%H%MZ")
    signals: list[dict] = []
    errors: list[str] = []
    baselines: list[str] = []
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
                continue
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
