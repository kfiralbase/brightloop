"""The web app (app/, exported from Base44) runs a copy of the core in the browser. Fail when that
copy no longer matches the repo, so a core change can't silently leave the app behind.
Fix: python3 scripts/browser_bundle.py, put it in the app's public/py/bundle.json, re-export."""

import json
import unittest
from pathlib import Path

from brightloop.file_run import BROWSER_FILES

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "app/public/py/bundle.json"


@unittest.skipUnless(BUNDLE.exists(), "app/ not exported")
class AppCopy(unittest.TestCase):
    def test_app_runs_the_same_core_as_the_repo(self):
        files = json.loads(BUNDLE.read_text(encoding="utf-8"))["files"]
        self.assertEqual(sorted(files), sorted(BROWSER_FILES))
        for rel in BROWSER_FILES:
            self.assertEqual(files[rel], (ROOT / rel).read_text(encoding="utf-8"), f"{rel} differs in the app's copy")


if __name__ == "__main__":
    unittest.main()
