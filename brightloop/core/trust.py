"""How much a signal's source can be trusted.

Maya's rule: "if it's on their pricing page and it moved, I flag it." So the only
source that can carry a pricing change on its own is the competitor's own pricing page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import slug

# Known official domains. Competitors not listed fall back to name matching,
# so unseen competitors in an input file are still judged by the same rule.
OFFICIAL_DOMAINS: dict[str, tuple[str, ...]] = {
    "lovable": ("lovable.dev", "lovable.app"),
    "replit": ("replit.com", "blog.replit.com", "docs.replit.com"),
    "bolt": ("bolt.new", "stackblitz.com"),
    "v0": ("v0.app", "v0.dev", "vercel.com"),
}

# Platforms where anyone can post. An official account here is still not a pricing page.
SOCIAL_DOMAINS = {
    "x.com", "twitter.com", "reddit.com", "linkedin.com", "facebook.com", "instagram.com",
    "youtube.com", "medium.com", "substack.com", "news.ycombinator.com", "threads.net",
}

_DOMAIN = re.compile(r"(?<![@\w])((?:[a-z0-9-]+\.)+[a-z]{2,})(/[^\s,;]*)?", re.IGNORECASE)
_PAID = re.compile(r"\b(sponsored|promoted|advertorial|paid post|ad network|affiliate)\b", re.I)
_UNVETTED = re.compile(r"\b(guest post|u/anon|anonymous|unverified|rumou?r|forum)\b", re.I)
# The pricing page itself: the path starts with "/pricing", optionally after a locale ("/pricing",
# "/en/pricing/", "/pricing?ref=x"). Not a blog post that starts with the word ("/pricing-update")
# or ends with it ("/blog/pricing"), and not on a blog or docs subdomain.
_PRICING_PATH = re.compile(r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(pricing|plans|price|billing)(?=/|\?|#|$)", re.I)
_CONTENT_HOST = re.compile(r"^(blog|docs|help|support|community|changelog|news)\.", re.I)

OFFICIAL_PRICING = "official_pricing_page"
OFFICIAL_OTHER = "official_other"
THIRD_PARTY = "third_party"


@dataclass(frozen=True)
class SourceInfo:
    tier: str
    domain: str | None
    path: str
    paid: bool
    unvetted: bool
    placeholder: bool  # reserved example domains (*.example) are never real sources


def _is_official(domain: str, path: str, competitor: str) -> bool:
    key = slug(competitor)
    known = OFFICIAL_DOMAINS.get(key)
    if known:
        return any(domain == d or domain.endswith("." + d) for d in known)
    labels = domain.split(".")[:-1]
    return bool(key) and key.replace("-", "") in [label.replace("-", "") for label in labels]


def classify_source(raw: object, competitor: object) -> SourceInfo:
    text = raw if isinstance(raw, str) else ""
    m = _DOMAIN.search(text)
    domain = m.group(1).lower().removeprefix("www.") if m else None
    path = (m.group(2) or "") if m else ""
    paid = bool(_PAID.search(text))
    unvetted = bool(_UNVETTED.search(text))
    placeholder = bool(domain and (domain.endswith(".example") or domain == "example.com"))

    tier = THIRD_PARTY
    if domain and not placeholder and not paid:
        if domain in SOCIAL_DOMAINS:
            handle = re.search(r"@([a-z0-9_]+)", path, re.I)
            if handle and slug(competitor).replace("-", "") in handle.group(1).lower():
                tier = OFFICIAL_OTHER
        elif _is_official(domain, path, str(competitor or "")):
            on_page = _PRICING_PATH.search(path) and not _CONTENT_HOST.match(domain)
            tier = OFFICIAL_PRICING if on_page else OFFICIAL_OTHER
    return SourceInfo(tier, domain, path, paid, unvetted, placeholder)
