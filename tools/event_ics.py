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
    while raw:
        cut = 75 if not out else 74
        if len(raw) <= cut:
            piece = raw
            raw = b""
        else:
            cut = min(cut, len(raw))
            while cut > 0 and (raw[cut] & 0xC0) == 0x80:
                cut -= 1
            if cut <= 0:
                cut = 1
            piece, raw = raw[:cut], raw[cut:]
        out.append((" " if out else "") + piece.decode("utf-8"))
    return "\r\n".join(out)


def _location(event):
    if event.get("online") and not (event.get("place") or event.get("city")):
        return "Online"
    parts = [event.get("place") or "", event.get("city") or ""]
    parts = [p.strip() for p in parts if isinstance(p, str) and p.strip()]
    if event.get("online") and parts and "online" not in parts[0].lower():
        parts.append("Online")
    return ", ".join(dict.fromkeys(parts))


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
        loc = _location(event)
        if loc:
            lines.append("LOCATION:" + _escape(loc))
        url = event.get("url") or ""
        if isinstance(url, str) and url.startswith("https://"):
            lines.append("URL:" + url)
        note = redact(event.get("note") or "")
        if note:
            lines.append("DESCRIPTION:" + _escape(note))
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
