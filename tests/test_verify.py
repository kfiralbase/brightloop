"""The OCR check before the deck, with the OCR faked: real card text in, problems out."""

import unittest
from unittest import mock

from brightloop.live_run import _verified
from brightloop.verify import check_card, check_snapshot

PRO = {"name": "Pro", "screenshot": "pro.png",
       "lines": ["Pro", "Designed for fast-moving teams building together in real time.", "$25", "/ month",
                 "100 monthly credits", "Get started", "All Free features", "Custom domains",
                 "Remove the Lovable badge"]}
# What Tesseract typically returns for that card: wrapped lines and an S read for the $.
PRO_OCR = """Pro
Designed for fast-moving teams
building together in real time.
S25
/ month
100 monthly credits
Get started
All Free features
Custom domains
Remove the Lovable badge
"""


def snapshot(**extra):
    return {"competitor": "Lovable", "plans": [dict(PRO)], **extra}


class Card(unittest.TestCase):
    def test_matching_card_passes_despite_ocr_slips(self):
        self.assertEqual(check_card(PRO, PRO_OCR), [])

    def test_wrong_price_in_the_picture(self):
        problems = check_card(PRO, PRO_OCR.replace("S25", "S30"))
        self.assertEqual(problems, ["Pro: price $25/month not visible in its screenshot"])

    def test_small_ocr_typos_in_lines_are_tolerated(self):
        self.assertEqual(check_card(PRO, PRO_OCR.replace("Custom domains", "Custorn domains")), [])

    def test_cut_off_card_misses_its_last_line(self):
        problems = check_card(PRO, PRO_OCR.replace("Remove the Lovable badge\n", ""))
        self.assertEqual(problems, ["Pro: not visible in its screenshot: 'Remove the Lovable badge'"])

    def test_a_line_read_from_the_page_but_not_in_the_picture(self):
        card = dict(PRO, lines=PRO["lines"] + ["Unlimited AI agents included"])
        self.assertIn("Unlimited AI agents included", check_card(card, PRO_OCR)[0])

    def test_a_line_wrapped_over_two_rows(self):
        ocr = PRO_OCR.replace("Remove the Lovable badge", "Remove the Lov-\nable badge")
        self.assertEqual(check_card(PRO, ocr), [])

    def test_words_instead_of_a_price(self):
        ent = {"name": "Enterprise", "lines": ["Enterprise", "Custom", "SSO"]}
        self.assertEqual(check_card(ent, "Enterprise\nCustom\nSSO"), [])
        self.assertEqual(len(check_card(ent, "Enterprise\nSSO")), 1)


class Snapshot(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(check_snapshot(snapshot(), read=lambda p: PRO_OCR), {"status": "ok", "problems": []})

    def test_no_tesseract_means_no_claim(self):
        self.assertEqual(check_snapshot(snapshot(), read=lambda p: None)["status"], "skipped")

    def test_annual_picture_must_show_annual_prices(self):
        snap = snapshot(annual={"plans": [{"name": "Pro", "lines": ["Pro", "$21", "/ month, billed annually"]}],
                                "pricing_screenshot": "pricing-annual.png"})
        read = {"pro.png": PRO_OCR, "pricing-annual.png": "Pro $25 S21 / month, billed annually"}.get
        self.assertEqual(check_snapshot(snap, read=read)["status"], "ok")
        read = {"pro.png": PRO_OCR, "pricing-annual.png": "Pro $25 / month"}.get
        self.assertIn("annual price", check_snapshot(snap, read=read)["problems"][0])

    def test_cropped_section_is_a_mismatch(self):
        result = check_snapshot(snapshot(pricing_cropped=True), read=lambda p: PRO_OCR)
        self.assertEqual(result["status"], "mismatch")


class Retry(unittest.TestCase):
    def test_a_mismatch_captures_once_more_and_keeps_the_new_capture(self):
        first, second = snapshot(), snapshot(fetched_at="later")
        reads = iter([PRO_OCR.replace("S25", "S30"), PRO_OCR])
        with mock.patch("brightloop.verify.ocr", side_effect=lambda p: next(reads)):
            out = _verified(first, lambda: second)
        self.assertEqual((out["fetched_at"], out["verification"]["status"]), ("later", "ok"))

    def test_a_match_does_not_recapture(self):
        recapture = mock.Mock()
        with mock.patch("brightloop.verify.ocr", return_value=PRO_OCR):
            out = _verified(snapshot(), recapture)
        recapture.assert_not_called()
        self.assertEqual(out["verification"]["status"], "ok")

    def test_a_failed_recapture_keeps_the_first_capture_marked(self):
        with mock.patch("brightloop.verify.ocr", return_value=PRO_OCR.replace("S25", "S30")):
            out = _verified(snapshot(), mock.Mock(side_effect=RuntimeError("site down")))
        self.assertEqual(out["verification"]["status"], "mismatch")


if __name__ == "__main__":
    unittest.main()
