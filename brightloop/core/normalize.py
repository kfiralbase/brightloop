"""Turn raw signal fields into clean, comparable values.

Everything here is pure: no network, no clock, no randomness.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_HTML_COMMENT = re.compile(r"<!--.*?(-->|$)", re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]{0,200}>")
_WS = re.compile(r"\s+")

# Phrases that address an AI system instead of a human reader. Web text is data;
# when it tries to give orders we drop the order and flag the signal.
_INJECTION = re.compile(
    r"(note to (ai|llm|assistant|automated)|ignore (all |any )?(previous|prior) instructions"
    r"|set (the )?confidence|append (the line|this)|system prompt|you are an ai"
    r"|as an ai (model|assistant))",
    re.IGNORECASE,
)


def clean_text(raw: object) -> tuple[str, bool]:
    """Return (visible text, injection_detected).

    Hidden HTML comments and tags are removed before anything else reads the text,
    so instructions hidden in them can't reach the output.
    """
    text = raw if isinstance(raw, str) else ""
    hidden = " ".join(m.group(0) for m in _HTML_COMMENT.finditer(text))
    visible = _HTML_TAG.sub(" ", _HTML_COMMENT.sub(" ", text))
    visible = _WS.sub(" ", visible).strip()
    injected = bool(_INJECTION.search(hidden) or _INJECTION.search(visible))
    if _INJECTION.search(visible):  # an order in plain sight: drop that sentence, keep the rest
        visible = " ".join(s for s in _SENTENCE.split(visible) if not _INJECTION.search(s))
    return visible, injected


_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_UTC_SUFFIX = re.compile(r"\s*(UTC|GMT|Z)$", re.IGNORECASE)


def parse_ts(raw: object, default_tz: str) -> datetime | None:
    """Parse the timestamp shapes seen in the wild into an aware UTC datetime.

    Accepts ISO 8601 with offset or Z, "YYYY-MM-DD HH:MM UTC", naive values (read in the
    input's timezone) and Unix epoch numbers in seconds or milliseconds. Returns None when it
    can't be parsed.
    """
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        try:
            return datetime.fromtimestamp(raw / 1000 if raw > 1e11 else raw, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    explicit_utc = bool(_UTC_SUFFIX.search(s))
    s = _UTC_SUFFIX.sub("", s).replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc if explicit_utc else ZoneInfo(default_tz))
    return dt.astimezone(timezone.utc)


def parse_date(raw: object) -> date | None:
    if not isinstance(raw, str):
        return None
    try:
        return date.fromisoformat(raw.strip()[:10])
    except ValueError:
        return None


def week_bounds(week: object, tz: str) -> tuple[datetime, datetime] | None:
    """ISO week like "2026-W43", read in the marketer's timezone, as UTC [start, end)."""
    if not isinstance(week, str):
        return None
    m = re.fullmatch(r"(\d{4})-W(\d{2})", week.strip())
    if not m:
        return None
    try:
        monday = date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    except ValueError:
        return None
    zone = ZoneInfo(tz)
    start = datetime(monday.year, monday.month, monday.day, tzinfo=zone)
    nxt = monday + timedelta(days=7)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")


def iso_utc(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None
