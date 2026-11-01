"""Event location check: a physical event needs a street address (or stored
coordinates), not only a venue name. A bare name like "Vingtor" makes the map
search land on whatever else carries that name.

VENUES adds the street for venues whose source lists only the name. Each entry
names where the address was read. geocode_issue() is optional (network, Nominatim)
and flags an address that geocodes far from the stated city.
"""
import json
import math
import re
import time
import urllib.parse
import urllib.request

# name (lowercase) -> (city, street address, where it was read)
VENUES = {
    "vingtor": ("Stavanger", "Børehaugen 1A, 4006 Stavanger", "https://vingtorarbeidsbar.no/no/contact-us/"),
    "oslo science park": ("Oslo", "Gaustadalléen 21, 0349 Oslo", "https://forskningsparken.no/"),
}

_STREET = re.compile(r"[^\W\d_]{2,}\.?\s+\d+[A-Za-z]?\b", re.UNICODE)  # "Børehaugen 1A", "gate 7"


def with_address(place, city):
    """Place plus the known street when the place is only a venue name from VENUES."""
    p = (place or "").strip()
    name = p.split(",")[0].strip()
    v = VENUES.get(name.lower())
    if v and not has_street(p) and (not city or v[0].lower() == city.strip().lower()):
        return f"{name}, {v[1]}"
    return place


def has_street(place):
    return bool(_STREET.search(place or ""))


def _has_coords(e):
    return any(e.get(k) not in (None, "", [], {}) for k in ("lat", "latitude", "geo", "coordinates"))


def issue(e):
    """None when the location is usable for a map link, else a short reason.
    Online events and city-only rows (venue not announced) are not flagged."""
    if e.get("online"):
        return None
    place = (e.get("place") or "").strip()
    city = (e.get("city") or "").strip()
    if not place:
        return None if e.get("online") else "no place"
    if place.lower() == city.lower() or _has_coords(e) or has_street(place):
        return None
    return f"venue without street address: {place!r}"


def _geocode(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "nordiccrypto.no location check"})
    with urllib.request.urlopen(req, timeout=20) as r:
        hits = json.load(r)
    time.sleep(1.1)  # Nominatim policy: at most one request per second
    return (float(hits[0]["lat"]), float(hits[0]["lon"])) if hits else None


def _km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _street_query(place, city):
    """The address part of the place: from the first segment with a street number."""
    parts = [x.strip() for x in place.split(",")]
    for x in reversed(parts):
        if has_street(x):
            return f"{re.sub(r'\s*\(.*?\)', '', x)}, {city}"
    return f"{place}, {city}"


def geocode_issue(e, max_km=25):
    """Network check. None when the address geocodes within max_km of the city."""
    place, city = (e.get("place") or "").strip(), (e.get("city") or "").strip()
    if not place or not city or place.lower() == city.lower():
        return None
    town = _geocode(city)
    spot = _geocode(_street_query(place, city))
    if not town or not spot:
        return f"address not found: {_street_query(place, city)!r}"
    d = _km(town, spot)
    return None if d <= max_km else f"address is {d:.0f} km from {city}"


if __name__ == "__main__":
    import sys
    bad = 0
    for f in [a for a in sys.argv[1:] if not a.startswith("--")] or ["data/events.json"]:
        for e in json.load(open(f, encoding="utf-8"))["events"]:
            why = issue(e) or ("--geocode" in sys.argv and geocode_issue(e)) or None
            if why:
                bad += 1
                print(f"{f} {e.get('id')} {why}")
    sys.exit(1 if bad else 0)
