"""The file test: cases.json in, result dict out.

The one function behind both `./run --input ... --output ...` and the web app's
"Test a file" page, which runs this same file in the browser with Pyodide.
Keep its imports inside BROWSER_FILES so the browser copy stays complete.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .core import BUILT_FOR, run
from .sources import file as file_source

# Everything run_file needs, relative to the repo root. The web app ships exactly these files.
BROWSER_FILES = [
    "brightloop/__init__.py",
    "brightloop/file_run.py",
    "brightloop/core/__init__.py",
    "brightloop/core/normalize.py",
    "brightloop/core/pipeline.py",
    "brightloop/core/pricing.py",
    "brightloop/core/trust.py",
    "brightloop/sources/__init__.py",
    "brightloop/sources/file.py",
]


def run_file(input_path: str) -> dict:
    payload, load_errors = file_source.load(input_path)
    started = datetime.now(timezone.utc)
    try:
        result = run(payload, started_at=started)
    except Exception as exc:  # noqa: BLE001 - a bug must still leave a valid result file
        result = _fallback(payload, started, exc)
    result["run"]["errors"][:0] = load_errors
    result["run"]["mode"] = "file"
    return result


def _fallback(payload: object, started: datetime, exc: Exception) -> dict:
    """The output contract even when the decision code itself fails: every id the input gave is
    placed in skipped, so nothing disappears, and the failure is stated in run.errors."""
    ids: list[str] = []
    signals = payload.get("signals") if isinstance(payload, dict) else None
    for s in signals if isinstance(signals, list) else []:
        sid = s.get("id") if isinstance(s, dict) else None
        if isinstance(sid, (int, float)) and not isinstance(sid, bool):
            sid = str(sid)
        if isinstance(sid, str) and sid.strip() and sid not in ids:
            ids.append(sid)
    reason = "Not processed: the run stopped on an internal error (see run.errors)."
    return {
        "built_for": BUILT_FOR,
        "items": [],
        "skipped": [{"id": sid, "reason": reason} for sid in ids],
        "run": {"started_at": started.isoformat(timespec="seconds"), "cost_usd": 0.0,
                "errors": [f"Internal error: {type(exc).__name__}: {exc}"]},
    }
