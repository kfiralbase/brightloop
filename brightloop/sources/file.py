"""Read a cases.json file. The only thing test mode does differently from live mode."""

from __future__ import annotations

import json
from pathlib import Path


def load(path: str | Path) -> tuple[object, list[str]]:
    """Return (payload, errors). A broken file gives payload None and an error, never a crash."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [f"Input file not found: {path}"]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"Input file is not valid JSON: {exc}"]
