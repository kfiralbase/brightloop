"""The Monday Slack message: the link, what moved, what wasn't checked, or why there's no deck."""

import json
import unittest

from brightloop.notify import deck_message, post

DECK = {"ok": True, "name": "Competitor Deck Wk of Oct 26, 2026",
        "deck_url": "https://docs.google.com/presentation/d/x/edit", "lines": [], "not_checked": []}


class Message(unittest.TestCase):
    def test_quiet_week_still_links_the_deck(self):
        text = deck_message(DECK)
        self.assertIn("<https://docs.google.com/presentation/d/x/edit|open the deck>", text)
        self.assertIn("No pricing changes this week.", text)

    def test_changes_and_not_checked_sites_are_listed(self):
        deck = dict(DECK, lines=[{"competitor": "Lovable", "deck_line": "Pro: $25→$30/month (spotted Thu)"}],
                    not_checked=["Bolt"])
        text = deck_message(deck)
        self.assertIn("• Lovable: Pro: $25→$30/month (spotted Thu)", text)
        self.assertIn("Not checked this week (site didn't load): Bolt.", text)
        self.assertNotIn("No pricing changes", text)

    def test_unverified_slides_are_named(self):
        self.assertIn("Check before 11: the screenshot doesn't match the page text for Bolt",
                      deck_message(dict(DECK, unverified=["Bolt"])))

    def test_failed_deck_says_so_and_points_to_the_app(self):
        for deck in (None, {"ok": False, "error": "Deck: Drive quota"}):
            text = deck_message(deck)
            self.assertIn("couldn't be built", text)
            self.assertIn("bright-loop-watch.base44.app", text)

    def test_post_sends_slack_json(self):
        sent = []

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b"ok"

        post("https://hooks.slack.test/T/B/x", "hi", opener=lambda r: (sent.append(r), Resp())[1])
        self.assertEqual(json.loads(sent[0].data), {"text": "hi"})


if __name__ == "__main__":
    unittest.main()
