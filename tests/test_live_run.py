"""The live run's offline replay: real recording layout, no network, no Playwright."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brightloop.live_run import carry_homepage, live
from brightloop.store.records import to_records
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


class SiteDidntLoad(unittest.TestCase):
    """Maya: last week's screenshot marked "not checked" beats an empty slide."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.config = self.tmp / "live.json"
        write(self.config, {"timezone": "Asia/Jerusalem",
                            "competitors": [{"name": "Lovable", "url": "https://lovable.dev/pricing", "enabled": True}]})
        last = dict(copy.deepcopy(LOVABLE), pricing_screenshot_url="https://cdn/p.png",
                    homepage_screenshot_url="https://cdn/h.png")
        write(self.tmp / "rec/lovable/2026-10-19T0430Z/snapshot.json", last)

    def run_live(self, stamp, capture):
        with mock.patch.dict("os.environ", {"BRIGHTLOOP_RUN_KEY": stamp}), \
             mock.patch("brightloop.sources.live.capture", capture):
            return live(self.config, self.tmp / "rec", None, offline=False)

    def test_last_weeks_snapshot_stands_in_marked_not_checked(self):
        result = self.run_live("2026-10-26T0430Z", mock.Mock(side_effect=RuntimeError("bot check")))
        self.assertIn("capture failed", result["run"]["errors"][0])
        self.assertIn("not checked this week", result["run"]["notes"][0])
        snap = json.loads((self.tmp / "rec/lovable/2026-10-26T0430Z/snapshot.json").read_text())
        self.assertTrue(snap["not_checked"])
        self.assertEqual(snap["fetched_at"], LOVABLE["fetched_at"])  # the pictures' real age
        record = to_records("2026-10-26T0430Z", result, {"week": "2026-W44"}, [snap])["Snapshot"][0]
        self.assertEqual((record["not_checked"], record["pricing_screenshot_url"]), (True, "https://cdn/p.png"))

    def test_next_week_compares_against_the_last_real_capture(self):
        self.run_live("2026-10-26T0430Z", mock.Mock(side_effect=RuntimeError("down")))
        fresh = dict(copy.deepcopy(LOVABLE), fetched_at="2026-11-02T04:30:00Z")
        fresh["plans"][1]["lines"] = [("$30" if l == "$25" else l) for l in fresh["plans"][1]["lines"]]
        result = self.run_live("2026-11-02T0430Z", mock.Mock(return_value=fresh))
        self.assertEqual([i["deck_line"] for i in result["items"]], ["Pro: $25→$30/month"])

    def test_no_earlier_capture_means_no_stand_in(self):
        for p in (self.tmp / "rec/lovable").glob("*/snapshot.json"):
            p.unlink()
        self.run_live("2026-10-26T0430Z", mock.Mock(side_effect=RuntimeError("down")))
        self.assertFalse((self.tmp / "rec/lovable/2026-10-26T0430Z/snapshot.json").exists())


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
