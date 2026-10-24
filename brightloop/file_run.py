"""The file test: cases.json in, result dict out.

The one function behind both `./run --input ... --output ...` and the web app's
"Test a file" page, which runs this same file in the browser with Pyodide.
Keep its imports inside BROWSER_FILES so the browser copy stays complete.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .core import run
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
    result = run(payload, started_at=datetime.now(timezone.utc))
    result["run"]["errors"][:0] = load_errors
    result["run"]["mode"] = "file"
    return result
