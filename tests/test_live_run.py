"""The live run's offline replay: real recording layout, no network, no Playwright."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from brightloop.live_run import carry_homepage, live
from tests.test_snapshots import LOVABLE


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class HomepageCarry(unittest.TestCase):
    def test_fresh_picture_is_dated_now(self):
        cur = {"fetched_at": "2026-10-26T04:30:00Z", "homepage_url": "https://x.dev/", "homepage_screenshot": "h.png"}
        self.assertIsNone(carry_homepage(None, cur))
        self.assertEqual(cur["homepage_captured_at"], "2026-10-26T04:30:00Z")

    def test_blocked_homepage_reuses_last_weeks_picture_and_says_so(self):
        prev = {"fetched_at": "2026-10-19T04:30:00Z", "homepage_screenshot_url": "https://cdn/h.png"}
        cur = {"fetched_at": "2026-10-26T04:30:00Z", "homepage_url": "https://x.dev/", "homepage_screenshot": None}
        note = carry_homepage(prev, cur)
        self.assertEqual(cur["homepage_screenshot_url"], "https://cdn/h.png")
        self.assertEqual(cur["homepage_captured_at"], "2026-10-19T04:30:00Z")
        self.assertIn("2026-10-19", note)

    def test_nothing_to_reuse(self):
        cur = {"fetched_at": "2026-10-26T04:30:00Z", "homepage_url": "https://x.dev/", "homepage_screenshot": None}
        self.assertIn("none from earlier", carry_homepage({}, cur))
        self.assertNotIn("homepage_screenshot_url", cur)


class Replay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.config = self.tmp / "live.json"
        write(self.config, {"timezone": "Asia/Jerusalem", "utm_source": "brightloop",
                            "competitors": [{"name": "Lovable", "url": "https://lovable.dev/pricing", "enabled": True},
                                            {"name": "Bolt", "url": "https://bolt.new/pricing", "enabled": True}]})
        before = copy.deepcopy(LOVABLE)
        after = copy.deepcopy(LOVABLE)
        after["fetched_at"] = "2026-10-26T04:30:00Z"
        after["plans"][1]["lines"] = [("$30" if l == "$25" else l) for l in after["plans"][1]["lines"]]
        write(self.tmp / "rec/lovable/2026-10-19T0430Z/snapshot.json", before)
        write(self.tmp / "rec/lovable/2026-10-26T0430Z/snapshot.json", after)

    def test_replay_finds_the_recorded_change_without_network(self):
        out = self.tmp / "result.json"
        result = live(self.config, self.tmp / "rec", out, offline=True)
        self.assertEqual(result["run"]["mode"], "replay")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["change"]["after"], "$30/month")
        self.assertTrue(any("Bolt" in e for e in result["run"]["errors"]))  # one recording only
        self.assertEqual(json.loads(out.read_text())["built_for"], "maya")
        self.assertFalse((self.tmp / "rec/runs").exists())

    def test_replay_of_the_committed_recordings(self):
        root = Path(__file__).resolve().parent.parent
        result = live(root / "config/live.json", root / "recordings", None, offline=True)
        self.assertEqual(result["built_for"], "maya")
        for item in result["items"]:
            self.assertTrue(item["evidence"])


if __name__ == "__main__":
    unittest.main()
