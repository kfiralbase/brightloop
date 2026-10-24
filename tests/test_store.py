"""Publishing to Base44, with the network faked out."""

import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from brightloop.store.base44 import Base44Error, Base44Store
from brightloop.store.publish import publish_run
from brightloop.store.records import KEYS, to_records

SNAP = {"competitor": "Lovable", "url": "https://lovable.dev/pricing", "fetched_at": "2026-10-26T04:30:00Z",
        "billing_view": "monthly", "page_screenshot": "rec/lovable/S/page.png",
        "plans": [{"name": "Pro", "lines": ["Pro", "$30", "/ month"], "screenshot": "rec/lovable/S/pro.png"}]}
RESULT = {
    "built_for": "maya",
    "items": [{"id": "chg-lovable-pro-price-30-month", "source_ids": ["live-lovable-1"], "confidence": 0.95,
               "action": "Add a slide", "why": "Pro went up", "competitor": "Lovable",
               "change": {"field": "price", "plan": "Pro", "before": "$25/month", "after": "$30/month",
                          "direction": "up"},
               "evidence": [{"source_id": "live-lovable-1", "source": "lovable.dev/pricing",
                             "ts_utc": "2026-10-26T04:30:00Z", "screenshot": "rec/lovable/S/pro.png"}]}],
    "skipped": [{"id": "x-1", "reason": "Ad"}],
    "run": {"started_at": "2026-10-26T04:30:00+00:00", "cost_usd": 0.0, "errors": [], "mode": "live"},
}
CASES = {"week": "2026-W44", "signals": []}


class FakeStore:
    def __init__(self, fail=()):
        self.uploads, self.upserts, self.fail = [], [], set(fail)

    def upload(self, path):
        if "upload" in self.fail:
            raise Base44Error("upload down")
        self.uploads.append(path.name)
        return f"https://cdn.example/{path.name}"

    def upsert(self, entity, key, records):
        if entity in self.fail:
            raise Base44Error(f"{entity} down")
        self.upserts.append((entity, key, records))
        return len(records)


class Records(unittest.TestCase):
    def test_mapping_matches_the_app_entities(self):
        snap = dict(SNAP, page_screenshot_url="https://cdn.example/page.png",
                    plans=[dict(SNAP["plans"][0], screenshot_url="https://cdn.example/pro.png")])
        result = json.loads(json.dumps(RESULT))
        result["items"][0]["evidence"][0]["screenshot"] = "https://cdn.example/pro.png"
        r = to_records("2026-10-26T0430Z", result, CASES, [snap])
        self.assertEqual(r["Run"][0]["status"], "ok")
        self.assertEqual((r["Run"][0]["items_count"], r["Run"][0]["skipped_count"]), (1, 1))
        ch = r["Change"][0]
        self.assertEqual((ch["before"], ch["after"], ch["direction"]), ("$25/month", "$30/month", "up"))
        self.assertEqual(ch["source"], "https://lovable.dev/pricing")
        self.assertEqual(ch["screenshot_url"], "https://cdn.example/pro.png")
        self.assertEqual(r["Skipped"], [{"run_key": "2026-10-26T0430Z", "signal_id": "x-1", "reason": "Ad"}])
        self.assertEqual(r["Snapshot"][0]["plans"][0]["price"], "$30/month")
        self.assertEqual(r["Snapshot"][0]["plan_screenshots"], [{"name": "Pro", "url": "https://cdn.example/pro.png"}])

    def test_local_screenshot_paths_never_reach_base44(self):
        r = to_records("k", RESULT, CASES, [SNAP])
        self.assertEqual(r["Change"][0]["screenshot_url"], "")
        self.assertEqual(r["Snapshot"][0]["plan_screenshots"], [])


class Publish(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        rec = self.root / "rec"
        (rec / "lovable/S").mkdir(parents=True)
        (rec / "runs/S").mkdir(parents=True)
        (rec / "lovable/S/snapshot.json").write_text(json.dumps(SNAP))
        (rec / "lovable/S/pro.png").write_bytes(b"png")
        (rec / "lovable/S/page.png").write_bytes(b"png")
        (rec / "runs/S/cases.json").write_text(json.dumps(CASES))
        (rec / "runs/S/result.json").write_text(json.dumps(RESULT))
        self.rec = rec

    def test_uploads_then_upserts_with_run_last(self):
        store = FakeStore()
        errors = publish_run(store, self.rec / "runs/S", self.rec, self.root, ["Lovable", "Bolt"])
        self.assertEqual(errors, [])
        self.assertEqual(sorted(store.uploads), ["page.png", "pro.png"])
        self.assertEqual([e for e, _, _ in store.upserts], ["Snapshot", "Change", "Skipped", "Run"])
        self.assertEqual({e: k for e, k, _ in store.upserts}, KEYS)
        change = store.upserts[1][2][0]
        self.assertEqual(change["screenshot_url"], "https://cdn.example/pro.png")
        saved = json.loads((self.rec / "lovable/S/snapshot.json").read_text())
        self.assertEqual(saved["plans"][0]["screenshot_url"], "https://cdn.example/pro.png")

    def test_failures_are_reported_not_raised(self):
        store = FakeStore(fail={"upload", "Change"})
        errors = publish_run(store, self.rec / "runs/S", self.rec, self.root, ["Lovable"])
        self.assertTrue(any("upload" in e for e in errors))
        self.assertTrue(any("Change" in e for e in errors))
        run_record = next(r for e, _, r in store.upserts if e == "Run")[0]
        self.assertEqual(run_record["status"], "partial")
        self.assertTrue(run_record["errors"])

    def test_republishing_does_not_reupload(self):
        publish_run(FakeStore(), self.rec / "runs/S", self.rec, self.root, ["Lovable"])
        again = FakeStore()
        publish_run(again, self.rec / "runs/S", self.rec, self.root, ["Lovable"])
        self.assertEqual(again.uploads, [])


class Client(unittest.TestCase):
    def test_upsert_request_shape(self):
        sent = []

        def opener(req, timeout):
            sent.append(req)
            return io.BytesIO(b'{"created": 1, "updated": 0}')

        Base44Store("app123", "tok", opener=opener).upsert("Run", "run_key", [{"run_key": "k"}])
        req = sent[0]
        self.assertEqual(req.full_url, "https://app.base44.com/api/apps/app123/entities/Run/upsert")
        self.assertEqual(req.get_header("Authorization"), "Bearer tok")
        self.assertEqual(json.loads(req.data), {"key": "run_key", "records": [{"run_key": "k"}]})

    def test_http_error_becomes_base44error_without_the_token(self):
        def opener(req, timeout):
            raise HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"detail":"read-only key"}'))

        with self.assertRaises(Base44Error) as ctx:
            Base44Store("app123", "secret-tok", opener=opener).upsert("Run", "run_key", [{}])
        self.assertIn("403", str(ctx.exception))
        self.assertNotIn("secret-tok", str(ctx.exception))

    def test_from_env_needs_both_values(self):
        self.assertIsNone(Base44Store.from_env({"BASE44_APP_ID": "a"}))
        self.assertIsNotNone(Base44Store.from_env({"BASE44_APP_ID": "a", "BASE44_TOKEN": "t"}))


if __name__ == "__main__":
    unittest.main()
