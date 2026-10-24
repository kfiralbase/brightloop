"""Snapshot diff → signals → core. Shapes copied from real Lovable, Replit and Bolt cards."""

import copy
import unittest
from datetime import datetime, timezone

from brightloop.core import run
from brightloop.snapshots import diff, features, headline_price, is_plan

T0 = datetime(2026, 10, 26, 4, 30, tzinfo=timezone.utc)

LOVABLE = {
    "competitor": "Lovable", "url": "https://lovable.dev/pricing", "fetched_at": "2026-10-19T04:30:00Z",
    "billing_view": "monthly",
    "plans": [
        {"name": "Free", "lines": ["Free", "Discover what Lovable can do for you", "$0", "Get started",
                                   "5 lovable.app domains", "Community support"]},
        {"name": "Pro", "lines": ["Pro", "Designed for fast-moving teams building together in real time.", "$25",
                                  "/ month", "100 monthly credits", "Get started", "All Free features",
                                  "Custom domains", "Remove the Lovable badge"], "screenshot": "shots/pro.png"},
        {"name": "Business", "lines": ["Business", "$50", "/ month", "100 monthly credits", "SSO",
                                       "Design templates"]},
    ],
}


def changed(**edits):
    snap = copy.deepcopy(LOVABLE)
    snap["fetched_at"] = "2026-10-26T04:30:00Z"
    for name, fn in edits.items():
        plan = next(p for p in snap["plans"] if p["name"] == name)
        plan["lines"] = fn(plan["lines"])
    return snap


def decide(signals):
    return run({"week": "2026-W44", "timezone": "Asia/Jerusalem", "signals": signals}, started_at=T0)


class CardParsing(unittest.TestCase):
    def test_headline_price_shapes(self):
        self.assertEqual(headline_price(["Pro", "$25", "/ month", "100 monthly credits"]), "$25/month")
        self.assertEqual(headline_price(["Core", "$20 / month", "$20 towards more powerful models"]), "$20/month")
        self.assertEqual(headline_price(["Pro", "$25", "*", "/month", "Billed monthly"]), "$25/month")
        self.assertEqual(headline_price(["Enterprise", "Custom", "Book a Demo"]), "Custom")

    def test_features_drop_ctas_badges_and_blurbs(self):
        f = features(LOVABLE["plans"][1]["lines"], "$25/month")
        self.assertEqual(f, ["100 monthly credits", "Custom domains", "Remove the Lovable badge"])


class Diffing(unittest.TestCase):
    def test_no_change_no_signals(self):
        signals, errors = diff(LOVABLE, changed())
        self.assertEqual((signals, errors), ([], []))

    def test_price_change_becomes_a_high_confidence_item(self):
        signals, _ = diff(LOVABLE, changed(Pro=lambda ls: [("$30" if l == "$25" else l) for l in ls]))
        self.assertEqual([s["text"] for s in signals], ["Pro plan shown at $30/month (was $25/month last week)."])
        self.assertEqual(signals[0]["source"], "lovable.dev/pricing")
        self.assertEqual(signals[0]["screenshot"], "shots/pro.png")
        item = decide(signals)["items"][0]
        self.assertEqual((item["change"]["before"], item["change"]["after"]), ("$25/month", "$30/month"))
        self.assertGreaterEqual(item["confidence"], 0.9)
        self.assertEqual(item["evidence"][0]["screenshot"], "shots/pro.png")

    def test_credit_cut_is_a_limit_change(self):
        signals, _ = diff(LOVABLE, changed(Pro=lambda ls: [("50 monthly credits" if l == "100 monthly credits" else l)
                                                            for l in ls]))
        item = decide(signals)["items"][0]
        self.assertEqual(item["change"]["field"], "credits")
        self.assertEqual(item["change"]["direction"], "down")

    def test_feature_moving_between_tiers(self):
        signals, _ = diff(LOVABLE, changed(Pro=lambda ls: [l for l in ls if l != "Custom domains"],
                                           Business=lambda ls: ls + ["Custom domains"]))
        self.assertEqual([s["text"] for s in signals], ["'Custom domains' moved from Pro to Business."])
        item = decide(signals)["items"][0]
        self.assertEqual(item["change"]["field"], "tier")

    def test_feature_removed_is_packaging_with_lower_confidence(self):
        signals, _ = diff(LOVABLE, changed(Pro=lambda ls: [l for l in ls if l != "Remove the Lovable badge"]))
        item = decide(signals)["items"][0]
        self.assertEqual(item["change"]["field"], "packaging")
        self.assertLess(item["confidence"], 0.9)

    def test_new_and_removed_plans(self):
        cur = changed()
        cur["plans"].append({"name": "Teams", "lines": ["Teams", "$40", "/ month", "Shared credits"]})
        signals, _ = diff(LOVABLE, cur)
        self.assertEqual(signals[0]["text"], "New Teams plan added to the pricing page at $40/month.")
        self.assertEqual(len(decide(signals)["items"]), 1)

    def test_copy_edits_are_not_changes(self):
        signals, _ = diff(LOVABLE, changed(Pro=lambda ls: [
            ("Built for fast-moving teams shipping together, in real time." if l.startswith("Designed") else l)
            for l in ls]))
        self.assertEqual(signals, [])

    def test_dropdown_values_are_not_features(self):
        # Replit Pro's "Credit tier" dropdown shows "$100 credits": a choice, not part of the plan.
        lines = ["Pro", "$100 / month", "10 parallel agents", "$100 credits", "Upgrade to Pro"]
        self.assertEqual(features(lines, "$100/month", ["$100 credits"]), ["10 parallel agents"])
        # An older recording didn't mark controls; the new one does. Not a removal.
        old = copy.deepcopy(LOVABLE)
        new = changed()
        new["plans"][1]["controls"] = ["100 monthly credits"]
        new["plans"][1]["lines"] = [l for l in new["plans"][1]["lines"] if l != "100 monthly credits"]
        self.assertEqual(diff(old, new), ([], []))
        # Picking another tier in the dropdown isn't a change either.
        old["plans"][1]["controls"] = ["100 monthly credits"]
        new["plans"][1]["lines"].append("200 monthly credits")
        new["plans"][1]["controls"] = ["200 monthly credits"]
        self.assertEqual(diff(old, new)[0], [])

    def test_side_programs_are_not_plans(self):
        # "Lovable for campus" (contact sales) was in older recordings; dropping it is not a removal.
        prev = copy.deepcopy(LOVABLE)
        prev["plans"].append({"name": "Lovable for campus", "lines": ["Lovable for campus", "Contact sales"]})
        signals, errors = diff(prev, changed())
        self.assertEqual((signals, errors), ([], []))
        self.assertFalse(is_plan("Lovable for students", ["Up to 50% off Lovable Pro", "Get started"]))
        self.assertTrue(is_plan("Enterprise", ["Enterprise", "Custom"]))
        self.assertTrue(is_plan("Launch", ["Launch", "$12 / month"]))

    def test_extraction_failure_is_not_reported_as_removals(self):
        cur = changed()
        cur["plans"] = cur["plans"][:1]
        signals, errors = diff(LOVABLE, cur)
        self.assertEqual(signals, [])
        self.assertIn("extraction problem", errors[0])

    def test_billing_view_switch_does_not_fake_a_price_change(self):
        cur = changed(Pro=lambda ls: [("$21" if l == "$25" else l) for l in ls])
        cur["billing_view"] = "default"
        signals, errors = diff(LOVABLE, cur)
        self.assertEqual(signals, [])
        self.assertIn("billing view changed", errors[0])

    def test_every_signal_id_is_unique_and_placed(self):
        cur = changed(Pro=lambda ls: [("$30" if l == "$25" else l) for l in ls if l != "Custom domains"],
                      Business=lambda ls: ls + ["Custom domains"])
        signals, _ = diff(LOVABLE, cur)
        ids = [s["id"] for s in signals]
        self.assertEqual(len(ids), len(set(ids)))
        r = decide(signals)
        placed = [i for it in r["items"] for i in it["source_ids"]] + [s["id"] for s in r["skipped"]]
        self.assertEqual(sorted(placed), sorted(ids))


if __name__ == "__main__":
    unittest.main()
