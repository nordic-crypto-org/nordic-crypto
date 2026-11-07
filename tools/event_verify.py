"""Which events may be written to D1, and how contact details are removed.

A row is ready only when the date, a clock time and the location were read from
the organiser or the venue. A civil day with no clock, a venue name with no
street, and a tip that was not checked do not qualify. An email address or a
phone number is removed before the row is stored or shown.
"""
import re

from tools import location_check

EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
# A phone has a space, a plus or parentheses. A bare date (2026-11-19) does not.
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact(text):
    """Drop email addresses and phone numbers. Dates and street numbers stay."""
    if not isinstance(text, str) or not text:
        return text

    def phone(match):
        raw = match.group(0)
        if not re.search(r"[+()\s]", raw):
            return raw
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 15:
            return ""
        return raw

    cleaned = PHONE.sub(phone, EMAIL.sub("", text))
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def redact_event(event):
    """Copy of the event with contact details removed from public text."""
    if not isinstance(event, dict):
        return event
    out = dict(event)
    for key in ("note", "title", "place", "organiser", "source"):
        if isinstance(out.get(key), str):
            out[key] = redact(out[key])
    desc = out.get("description")
    if isinstance(desc, str):
        out["description"] = redact(desc)
    elif isinstance(desc, dict) and isinstance(desc.get("text"), str):
        desc = dict(desc)
        desc["text"] = redact(desc["text"])
        out["description"] = desc
    notes = out.get("note_i18n")
    if isinstance(notes, dict):
        out["note_i18n"] = {k: redact(v) if isinstance(v, str) else v for k, v in notes.items()}
    return out


def has_clock(start):
    """True when start states an hour and minute. Midnight means a civil day, not a time."""
    if not isinstance(start, str):
        return False
    match = re.search(r"T(\d{2}):(\d{2})", start)
    if not match:
        return False
    return not (match.group(1) == "00" and match.group(2) == "00")


def location_stated(event):
    """Online, or a city plus a street (or a verified https map link)."""
    if not isinstance(event, dict):
        return False
    if event.get("online") is True:
        return True
    place = (event.get("place") or "").strip()
    city = (event.get("city") or "").strip()
    if not place or not city:
        return False
    if location_check.has_street(place):
        return True
    url = event.get("map_url") or ""
    return isinstance(url, str) and url.startswith("https://")


def verified_facts(event):
    """Date, clock time and location, from an https page, and not a tip."""
    if not isinstance(event, dict) or event.get("tip_only"):
        return False
    if not has_clock(event.get("start")) or not location_stated(event):
        return False
    url = event.get("url") or event.get("source_url") or ""
    return isinstance(url, str) and url.startswith("https://")


def _norm(value):
    return re.sub(r"\s+", " ", (value or "").casefold()).strip()


def dedupe_key(event):
    """title + calendar date + city. Online events share an empty city."""
    if not isinstance(event, dict):
        return ("", "", "")
    start = event.get("start") or ""
    return (_norm(event.get("title")), start[:10], _norm(event.get("city")))
