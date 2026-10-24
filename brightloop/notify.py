"""The one Monday message: Maya wants the deck in the folder "plus one Slack message with the
link—I'm not hunting through Drive on Monday morning." Posted to a Slack incoming webhook.

Only the scheduled Monday run sends it (she gets "a hundred pings a day"); Run now doesn't.
"""

from __future__ import annotations

import json
from urllib import request

from .store.base44 import USER_AGENT, _tls_context

APP_URL = "https://bright-loop-watch.base44.app"


def deck_message(deck: dict | None) -> str:
    """The message text, from build-deck's response. A failed deck is said plainly, with where
    to look instead, so a quiet Monday never means "something broke and nobody said"."""
    if not deck or not deck.get("ok"):
        why = (deck or {}).get("error") or "no response from the deck builder"
        return (f"The competitor deck couldn't be built this morning ({why}). "
                f"This week's pricing changes are in the app: {APP_URL}")
    out = [f"*{deck['name']}* is ready: <{deck['deck_url']}|open the deck>"]
    lines = deck.get("lines") or []
    out += [f"• {ln['competitor']}: {ln['deck_line']}" for ln in lines] or ["No pricing changes this week."]
    if deck.get("not_checked"):
        out.append(f"Not checked this week (site didn't load): {', '.join(deck['not_checked'])}. "
                   f"The slide shows the last screenshots, marked.")
    return "\n".join(out)


def post(webhook_url: str, text: str, opener=None) -> None:
    req = request.Request(webhook_url, data=json.dumps({"text": text}).encode(), method="POST",
                          headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    open_ = opener or (lambda r: request.urlopen(r, timeout=30, context=_tls_context()))
    with open_(req) as resp:
        resp.read()
