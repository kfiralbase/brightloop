"""Capture a competitor's pricing page: every plan card's text, plus a screenshot of each.

Live mode only. Needs Playwright (pip install -e '.[live]' && playwright install chromium).
The result is a plain JSON snapshot; everything after this step is pure and runs offline.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ..snapshots import PLAN_NAMES, is_plan

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

# Find plan cards: a short heading, grown to the largest ancestor that still holds only that
# one plan heading. That keeps the feature list with its price and stops before the grid.
_CARDS_JS = r"""
(planNames) => {
  const priceLike = /\$\s?\d|\bcustom\b|contact sales|book a demo|platform fee/i;
  const names = new Set(planNames.map(n => n.toLowerCase()));
  const own = el => (el.innerText || '').trim();
  const isHeading = el => /^H[1-6]$/.test(el.tagName) || el.getAttribute('role') === 'heading';
  // A plan label is a heading, or any element whose whole text is a known plan name and
  // none of whose children carries the same text (the innermost one).
  const heads = [...document.querySelectorAll('body *')].filter(el => {
    const t = own(el);
    if (!t || t.length > 30 || /\n/.test(t) || el.offsetParent === null) return false;
    if (el.closest('nav, header, footer, [role=navigation], [role=menu]')) return false;
    if (!isHeading(el) && !names.has(t.toLowerCase())) return false;
    return ![...el.children].some(c => own(c) === t);
  });
  const cardOf = h => {
    let card = h;
    while (card.parentElement && card.parentElement !== document.body) {
      const up = card.parentElement;
      if (heads.filter(o => up.contains(o)).length > 1) break;
      if ((up.innerText || '').length > 3000) break;
      card = up;
    }
    return card;
  };
  const seen = new Set(), seenNames = new Set(), out = [];
  heads.forEach((h, i) => {
    const card = cardOf(h);
    const text = (card.innerText || '').trim();
    const name = own(h).toLowerCase();
    // First card per plan name wins: later repeats are comparison tables and FAQs.
    if (seen.has(card) || seenNames.has(name) || !priceLike.test(text) || text.length < 10) return;
    seen.add(card);
    seenNames.add(name);
    card.setAttribute('data-bl-card', String(i));
    out.push({ name: h.innerText.trim(), text, index: i });
  });
  return out;
}
"""

_MONTHLY = re.compile(r"^\s*monthly\s*$", re.IGNORECASE)


def _prefer_monthly(page) -> bool:
    """Click a Monthly billing toggle if there is one, so weeks compare like for like."""
    for role in ("tab", "radio", "button", "switch"):
        loc = page.get_by_role(role, name=_MONTHLY)
        if loc.count():
            try:
                loc.first.click(timeout=3000)
                page.wait_for_timeout(800)
                return True
            except Exception:  # noqa: BLE001 - a missing toggle is not an error
                pass
    loc = page.get_by_text(_MONTHLY)
    if loc.count():
        try:
            loc.first.click(timeout=3000)
            page.wait_for_timeout(800)
            return True
        except Exception:  # noqa: BLE001
            pass
    return False


def capture(competitor: str, url: str, shots_dir: Path, *, timeout_ms: int = 45000) -> dict:
    """Open the page, read every plan card, screenshot each card. Raises on failure."""
    from playwright.sync_api import sync_playwright  # live-only dependency

    shots_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, user_agent=USER_AGENT)
            response = page.goto(url, wait_until="load", timeout=timeout_ms)
            status = response.status if response else None
            page.wait_for_function(r"() => /\$\s?\d/.test(document.body.innerText)", timeout=timeout_ms)
            monthly = _prefer_monthly(page)
            page.wait_for_timeout(1000)
            cards = page.evaluate(_CARDS_JS, PLAN_NAMES)
            plans = []
            for card in cards:
                if not is_plan(card["name"], _lines(card["text"])):
                    continue  # a side program (campus, students...), not a step on the price ladder
                shot = shots_dir / f"{_file_slug(card['name'])}.png"
                try:
                    page.locator(f"[data-bl-card='{card['index']}']").screenshot(path=str(shot), timeout=10000)
                    shot_path = str(shot)
                except Exception:  # noqa: BLE001 - keep the text even if the picture fails
                    shot_path = None
                plans.append({"name": card["name"], "lines": _lines(card["text"]), "screenshot": shot_path})
            full = shots_dir / "page.png"
            page.screenshot(path=str(full), full_page=True)
            return {
                "competitor": competitor,
                "url": url,
                "final_url": page.url,
                "status": status,
                "fetched_at": fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "billing_view": "monthly" if monthly else "default",
                "method": "playwright",
                "plans": plans,
                "page_screenshot": str(full),
            }
        finally:
            browser.close()


def _lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]


def _file_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "plan"
