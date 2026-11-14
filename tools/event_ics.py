"""iCal feed for the public calendar. The Worker serves the live copy from D1.
The build writes the same feed under /calendar.ics and /api/v1/events.ics so
the static site still has a file when the Worker cannot be reached.
"""
import datetime as dt
import os
import re

from tools.event_verify import redact

PRODID = "-//Nordic Crypto//Calendar//EN"


def _stamp(value):
    if isinstance(value, dt.datetime):
        when = value
    else:
        when = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return when.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text):
    text = redact(text or "") or ""
    text = text.replace("\\", "\\\\").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
    return text


def _fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out = []
    # Fold on UTF-8 boundaries so a multibyte character is not split.
    # Keep a TEXT escape (backslash + the next byte) on one physical line.
    while raw:
        cut = 75 if not out else 74
        if len(raw) <= cut:
            piece = raw
            raw = b""
        else:
            cut = min(cut, len(raw))
            while cut > 0 and (raw[cut] & 0xC0) == 0x80:
                cut -= 1
            if cut > 1 and raw[cut - 1] == 0x5C:
                cut -= 1
            if cut <= 0:
                cut = 1
            piece, raw = raw[:cut], raw[cut:]
        out.append((" " if out else "") + piece.decode("utf-8"))
    return "\r\n".join(out)


# A URI property value is written raw, so it must not carry anything that
# could end the content line: no whitespace, controls or Unicode line breaks.
_URI = re.compile(r"https://[^\s\x00-\x1f\x7f-\x9f\u2028\u2029]+")


def _uri(value):
    return value if isinstance(value, str) and _URI.fullmatch(value) else ""


def _https(value):
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return value if value.startswith("https://") else ""


def _location(event):
    place = event.get("place") if isinstance(event.get("place"), str) else ""
    city = event.get("city") if isinstance(event.get("city"), str) else ""
    place, city = place.strip(), city.strip()
    if event.get("online") and not place and not city:
        return "Online"
    parts = []
    if place:
        parts.append(place)
    if city and city not in parts:
        parts.append(city)
    if event.get("online") and parts and "online" not in parts[0].lower():
        parts.append("Online")
    return ", ".join(parts)


def _description(event, address):
    """Editor note, then the map link when the address is already in LOCATION."""
    note = (redact(event.get("note") or "") or "").strip()
    parts = [note] if note else []
    link = _https(event.get("map_url"))
    if link and address and link not in note:
        parts.append(link)
    return "\n".join(parts)


def render(events, now=None):
    """VCALENDAR text for published events that have a start. CRLF, folded at 75 octets."""
    now = now or dt.datetime.now(dt.timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:" + PRODID,
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Nordic Crypto",
    ]
    rows = [e for e in events or [] if isinstance(e, dict) and e.get("id") and e.get("start") and e.get("title")]
    rows.sort(key=lambda e: (e.get("start") or "", e.get("id") or ""))
    for event in rows:
        lines.append("BEGIN:VEVENT")
        lines.append("UID:" + re.sub(r"[^A-Za-z0-9]", "", str(event["id"])) + "@nordiccrypto.no")
        lines.append("DTSTAMP:" + _stamp(now))
        lines.append("DTSTART:" + _stamp(event["start"]))
        if event.get("end"):
            lines.append("DTEND:" + _stamp(event["end"]))
        lines.append("SUMMARY:" + _escape(event.get("title")))
        address = _location(event)
        loc = address or _https(event.get("map_url"))
        if loc:
            lines.append("LOCATION:" + _escape(loc))
        url = _uri(event.get("url"))
        if url:
            lines.append("URL:" + url)
        desc = _description(event, address)
        if desc:
            lines.append("DESCRIPTION:" + _escape(desc))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def write_feeds(site, events, now=None):
    """Static copies. The Worker is the live feed; these are the cache."""
    body = render(events, now=now)
    paths = [
        os.path.join(site, "calendar.ics"),
        os.path.join(site, "api", "v1", "events.ics"),
    ]
    for path in paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
    return paths
