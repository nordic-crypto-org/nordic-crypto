"""Official pages, press releases and public LinkedIn posts.

A page is kept only when it itself shows the date, a clock time and the
location (a street, or the word online). A LinkedIn sign-in wall is skipped.
Nothing is invented from the source config alone.
"""
import re

from tools.event_verify import redact

_TAG = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_MARKUP = re.compile(r"(?s)<[^>]+>")
_SPACE = re.compile(r"\s+")


def visible_text(html):
    text = _TAG.sub(" ", html or "")
    text = _MARKUP.sub(" ", text)
    return _SPACE.sub(" ", text).strip()


def linkedin_wall(html):
    """True when the response is a sign-in page rather than a public post."""
    text = (html or "").lower()
    if "authwall" in text or "linkedin.com/login" in text or "linkedin.com/uas/login" in text:
        return True
    if "join linkedin" in text and ("email or phone" in text or "sign in" in text):
        return True
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    if title and "linkedin" in title.group(1).lower() and "sign in" in title.group(1).lower():
        return True
    return False


def _clock_on_page(text, start):
    match = re.search(r"T(\d{2}):(\d{2})", start or "")
    if not match:
        return False
    hour, minute = match.group(1), match.group(2)
    if hour == "00" and minute == "00":
        return False
    return f"{hour}:{minute}" in text or f"{hour}.{minute}" in text


def _place_on_page(text, src):
    folded = text.casefold()
    if src.get("online"):
        return bool(re.search(r"\bonline\b|virtuel|virtuellt|digitalt|webinar", folded))
    place = src.get("event_place") or ""
    number = re.search(r"\d+[A-Za-z]?\b", place)
    if not number or number.group(0) not in text:
        return False
    words = re.findall(r"[^\W\d_]{4,}", place, re.UNICODE)
    return any(word.casefold() in folded for word in words)


def read_official_page(html, src):
    """(events, error). error is set only for a LinkedIn wall. A page that does
    not show every required fact returns no events and no error."""
    if not isinstance(src, dict):
        return [], None
    if src.get("type") == "linkedin-public" and linkedin_wall(html):
        return [], "not public without signing in"
    text = visible_text(html)
    folded = text.casefold()
    for needle in src.get("must_include") or []:
        if not isinstance(needle, str) or needle.casefold() not in folded:
            return [], None
    start = src.get("event_start") or ""
    if not _clock_on_page(text, start) or not _place_on_page(text, src):
        return [], None
    title = (src.get("event_title") or "").strip()
    if not title:
        return [], None
    event = {
        "title": redact(title),
        "start": start,
        "end": src.get("event_end") or None,
        "place": redact(src.get("event_place")) if src.get("event_place") else ("Online" if src.get("online") else None),
        "city": src.get("city"),
        "online": bool(src.get("online")),
        "organiser": redact(src.get("organiser")),
        "url": src.get("url"),
        "paid": src.get("paid") if "paid" in src else None,
        "description": "",
        "official_verified": True,
    }
    return [event], None
