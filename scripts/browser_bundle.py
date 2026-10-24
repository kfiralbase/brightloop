"""Pack the modules the web app's "Test a file" page runs (BROWSER_FILES) into one JSON file.

  python3 scripts/browser_bundle.py > bundle.json

The app loads it into Pyodide, writes each file, and calls brightloop.file_run.run_file:
the same code as ./run. Re-run this and replace public/py/bundle.json in the app whenever
one of these files changes; the page shows source_commit so a stale copy is visible.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brightloop.file_run import BROWSER_FILES  # noqa: E402

commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
files = {rel: (ROOT / rel).read_text(encoding="utf-8") for rel in BROWSER_FILES}
print(json.dumps({"source_repo": "kfiralbase/brightloop", "source_commit": commit, "files": files}))
