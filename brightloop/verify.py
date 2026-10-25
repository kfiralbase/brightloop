"""A last check before the deck: does each screenshot show what was read from the page text?

Live mode only, and on top of the existing logic: nothing here changes what is decided. Each plan
card's own screenshot is read back with OCR (Tesseract, if installed) and must show the plan's
price and every line under it. The annual pricing picture must show the annual prices, and the
pricing-section picture must hold every card (not cut off at the height limit). A failed check
marks the slide for Maya to look at; it never drops it ("an empty slide just gets me questions
I don't have answers to").
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

from .snapshots import features, headline_price, plans_of

# An OCR'd line this similar to a feature line counts as showing it. Every line under the price must
# be shown: on 282 lines from three real captures of all three sites, none was missed.
LINE_MATCH = 0.8
CROPPED = "pricing section taller than the screenshot limit: the slide shows it cut off"
_AMOUNT = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")


def ocr(path: str | Path | None) -> str | None:
    """The text in an image, or None when there's no image or no Tesseract."""
    if not path or not Path(path).exists() or not shutil.which("tesseract"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        try:
            image = _prepared(Path(path), Path(tmp) / "ocr.png")
            out = subprocess.run(["tesseract", str(image), "-", "--psm", "4"], capture_output=True, text=True,
                                 timeout=60, check=True)
        except (subprocess.SubprocessError, OSError):
            return None
    return out.stdout


def _prepared(src: Path, dst: Path) -> Path:
    """Card screenshots are small and some are light text on dark: Tesseract dropped big price digits
    and read almost nothing on dark cards. Gray, inverted when dark, three times larger, full contrast."""
    try:
        from PIL import Image, ImageOps, ImageStat  # live-only dependency, like Playwright
    except ImportError:
        return src
    im = Image.open(src).convert("L")
    if ImageStat.Stat(im).mean[0] < 128:
        im = ImageOps.invert(im)
    im = ImageOps.autocontrast(im.resize((im.width * 3, im.height * 3), Image.LANCZOS))
    im.save(dst)
    return dst


def _norm(text: str) -> str:
    """Undo the usual OCR slips before comparing: S or § read for $, O for 0 inside numbers, $ read
    for S in a word, a word split over two lines at a hyphen."""
    text = re.sub(r"[S§](?=\s?\d)", "$", text)
    text = re.sub(r"\b[S§$][Oo]\b", "$0", text)            # "$0" read as "SO"
    text = re.sub(r"(?<=\d)[Oo]|[Oo](?=\d)", "0", text)
    text = re.sub(r"(?<=\$\d) (?=\d)", "", text)            # "$18" read as "$1 8"
    text = re.sub(r"\$(?=[A-Za-z])", "s", text)
    text = re.sub(r"-\s*\n\s*", "-", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _shows_price(price: str | None, text: str) -> bool:
    if not price:
        return True
    m = _AMOUNT.search(price)
    if not m:  # "Custom", "Platform Fee": the words themselves
        return _norm(price) in text
    amount = re.escape(m.group(1))
    # Not part of a longer number ("$25" isn't found in "1025"), and "$0" needs its dollar sign:
    # a bare 0 is in nearly every card ("100 credits").
    pattern = r"\$\s?0" if m.group(1) == "0" else r"(?<![\d.,])\$?\s?" + amount
    return re.search(pattern + r"(?![\d.])", text) is not None


def _shows_line(line: str, text: str, ocr_lines: list[str]) -> bool:
    """A feature line wraps over two or three lines on a narrow card, so OCR'd lines are also
    compared two and three at a time."""
    want = _norm(line)
    if want in text:
        return True
    spans = [" ".join(ocr_lines[i:i + n]) for n in (1, 2, 3) for i in range(len(ocr_lines) - n + 1)]
    return any(SequenceMatcher(None, want, got).ratio() >= LINE_MATCH for got in spans)


def check_card(plan: dict, raw: str) -> list[str]:
    """Problems with one plan card's screenshot, compared with what was read from its text."""
    text = _norm(raw)
    ocr_lines = [_norm(ln) for ln in raw.splitlines() if ln.strip()]
    price = headline_price(plan["lines"])
    problems = []
    if not _shows_price(price, text):
        problems.append(f"{plan['name']}: price {price} not visible in its screenshot")
    lines = features(plan["lines"], price, plan.get("controls", []))
    missing = [ln for ln in lines if not _shows_line(ln, text, ocr_lines)]
    if missing:
        shown = "; ".join(f"'{ln}'" for ln in missing[:2]) + (f" and {len(missing) - 2} more" if len(missing) > 2 else "")
        problems.append(f"{plan['name']}: not visible in its screenshot: {shown}")
    return problems


def check_snapshot(snapshot: dict, read=None) -> dict:
    """{"status": "ok" | "mismatch" | "skipped", "problems": [...]} for one competitor's capture."""
    read = read or ocr
    problems: list[str] = []
    checked = 0
    for plan in plans_of(snapshot):
        raw = read(plan.get("screenshot"))
        if raw is None:
            continue
        checked += 1
        problems += check_card(plan, raw)
    # Annual prices: each card's own picture when there is one (OCR reads a single card far better
    # than the whole section: Bolt's "$18*" came back "$138" from the section, "$1 8" from the card).
    annual = snapshot.get("annual") or {}
    section = None
    for plan in annual.get("plans", []):
        raw = read(plan.get("screenshot"))
        if raw is None:
            if section is None:
                section = read(annual.get("pricing_screenshot")) or ""
            raw = section
        if not raw:
            continue
        checked += 1
        price = headline_price(plan["lines"])
        if not _shows_price(price, _norm(raw)):
            problems.append(f"{plan['name']}: annual price {price} not visible in the annual screenshot")
    if snapshot.get("pricing_cropped"):
        problems.append(CROPPED)
    if not checked:
        return {"status": "skipped", "problems": []}
    return {"status": "mismatch" if problems else "ok", "problems": problems}
