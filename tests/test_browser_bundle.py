"""The web app's "Test a file" page runs BROWSER_FILES in Pyodide. Check that those files alone
are enough, and that they give the same result as the CLI."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from brightloop.file_run import BROWSER_FILES

ROOT = Path(__file__).resolve().parent.parent

SCRIPT = """
import json, sys
sys.path.insert(0, sys.argv[2])
from brightloop.file_run import run_file
r = run_file(sys.argv[1])
r["run"].pop("started_at")
print(json.dumps(r, sort_keys=True))
"""


class BrowserBundle(unittest.TestCase):
    def test_bundle_alone_matches_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in BROWSER_FILES:
                dst = Path(tmp) / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, dst)
            fixture = str(ROOT / "tests/fixtures/brief_example.json")
            # -I: isolated, so only the copied files are importable, not the repo checkout.
            bundled = subprocess.run([sys.executable, "-I", "-c", SCRIPT, fixture, tmp],
                                     capture_output=True, text=True)
            self.assertEqual(bundled.returncode, 0, bundled.stderr)
            full = subprocess.run([sys.executable, "-I", "-c", SCRIPT, fixture, str(ROOT)],
                                  capture_output=True, text=True)
            self.assertEqual(json.loads(bundled.stdout), json.loads(full.stdout))


if __name__ == "__main__":
    unittest.main()
