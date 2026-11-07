"""Verified D1 writes, official-page discovery, the iCal feed and the seed.

  python3 -m unittest tests.test_event_d1_feed
"""
import json
import os
import shutil
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)

from tools import d1_store, event_discover, event_ics, event_verify
from tools.event_verify import dedupe_key, redact, verified_facts

AT = "2026-11-07T08:30:00+00:00"


def event(i, title="Meetup", **kw):
    row = {
        "id": i, "title": title, "start": "2026-11-19T18:00:00+01:00", "end": "2026-11-19T19:15:00+01:00",
        "place": "Sturegatan 15, 113 89 Stockholm", "city": "Stockholm", "country": "SE", "online": False,
        "organiser": "Unga Aktiesparare", "url": "https://example.org/e/" + i, "source": "Example",
        "status": "pending",
    }
    row.update(kw)
    return row


class Verify(unittest.TestCase):
    def test_redact_keeps_dates_and_drops_contacts(self):
        text = redact("Doors 2026-11-19 at 17:30. Write a@b.co or call +46 70 123 45 67.")
        self.assertIn("2026-11-19", text)
        self.assertNotIn("@", text)
        self.assertNotIn("123 45 67", text)

    def test_clock_place_and_tip(self):
        self.assertFalse(verified_facts(event("a", start="2026-11-19T00:00:00+01:00")))
        self.assertFalse(verified_facts(event("a", place="Bank Hotel", city="Stockholm")))
        self.assertFalse(verified_facts(event("a", tip_only=True)))
        self.assertTrue(verified_facts(event("a")))
        self.assertTrue(verified_facts(event("a", online=True, place=None, city=None)))
        self.assertEqual(dedupe_key(event("a", title="  Bitwise ")), dedupe_key(event("b", title="bitwise")))


class Discover(unittest.TestCase):
    PAGE = """
    <html><title>Launch</title><body>
    <p>Thursday, 19 November 2026. Doors open at 17:30 CET.</p>
    <p>La Voûte, Bank Hotel, Arsenalsgatan 6, 111 47 Stockholm</p>
    </body></html>
    """
    WALL = "<html><title>Sign In | LinkedIn</title><body>authwall join linkedin email or phone</body></html>"

    def src(self, **kw):
        base = {
            "type": "official-page", "url": "https://example.org/launch",
            "event_title": "Bitcoin Suisse Europe launches in the Nordics",
            "event_start": "2026-11-19T17:30:00", "event_place": "Arsenalsgatan 6, Stockholm",
            "city": "Stockholm", "organiser": "Bitcoin Suisse (Europe)", "online": False,
            "must_include": ["19 November 2026", "17:30", "Arsenalsgatan 6"],
        }
        base.update(kw)
        return base

    def test_page_confirms_time_and_street(self):
        rows, err = event_discover.read_official_page(self.PAGE, self.src())
        self.assertIsNone(err)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Bitcoin Suisse Europe launches in the Nordics")
        self.assertTrue(rows[0]["official_verified"])

    def test_missing_fact_emits_nothing(self):
        html = self.PAGE.replace("17:30", "evening")
        rows, err = event_discover.read_official_page(html, self.src())
        self.assertEqual((rows, err), ([], None))

    def test_linkedin_wall_is_not_a_source(self):
        rows, err = event_discover.read_official_page(self.WALL, self.src(type="linkedin-public"))
        self.assertEqual(rows, [])
        self.assertIn("signing in", err)


class Ics(unittest.TestCase):
    def test_feed_escapes_and_hides_email(self):
        body = event_ics.render([
            event("ab", title="A, B", note="Mail a@b.co", url="https://example.org/e"),
        ], now="2026-11-07T08:30:00+00:00")
        self.assertTrue(body.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertIn("SUMMARY:A\\, B", body)
        self.assertNotIn("a@b.co", body)
        self.assertIn("DTSTART:20261119T170000Z", body)
        self.assertIn("END:VCALENDAR", body)

    def test_static_files(self):
        with tempfile.TemporaryDirectory() as site:
            paths = event_ics.write_feeds(site, [event("ab")])
            self.assertTrue(all(os.path.exists(p) for p in paths))


class D1Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nc-evfeed-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.store = d1_store.open_sqlite(os.path.join(self.tmp, "c.sqlite"))

    def root(self, events):
        r = os.path.join(self.tmp, "root")
        shutil.rmtree(r, True)
        os.makedirs(os.path.join(r, "data"))
        os.makedirs(os.path.join(r, "archive"))
        d1_store.save_json(os.path.join(r, "data", "events.json"), {"events": events})
        d1_store.save_json(os.path.join(r, "archive", "events.json"), {"events": []})
        d1_store.save_json(os.path.join(r, "data", "news.json"), {"items": []})
        return r

    def test_schema_has_map_url(self):
        self.assertEqual(d1_store.schema_version(self.store), 5)
        cols = {row["name"] for row in self.store.query("PRAGMA table_info(events)")}
        self.assertIn("map_url", cols)

    def test_unverified_is_not_inserted_and_duplicate_updates(self):
        bare = event("new1", place="Hall", city="Oslo")  # no street
        good = event("new2", map_url="https://www.google.com/maps/search/?api=1&query=Sturegatan%2015")
        twin = event("new3", title=good["title"], url="https://example.org/other")
        root = self.root([bare, good])
        stats = d1_store.sync_root(self.store, root, AT, require_verified=True)
        self.assertEqual(stats["events"]["unverified"], 1)
        self.assertEqual(stats["events"]["inserted"], 1)
        stored = d1_store.one(self.store, "SELECT map_url, payload FROM events WHERE id = 'new2'")
        self.assertTrue(stored["map_url"].startswith("https://"))
        self.assertNotIn("new1", json.loads(stored["payload"])["title"])
        root = self.root([bare, twin])
        again = d1_store.sync_root(self.store, root, AT, require_verified=True)
        self.assertEqual(again["events"]["inserted"], 0)
        ids = [row["id"] for row in self.store.query("SELECT id FROM events")]
        self.assertEqual(ids, ["new2"])
        self.assertEqual(json.loads(d1_store.one(self.store, "SELECT payload FROM events")["payload"])["url"], twin["url"])

    def test_seed_moves_impact_and_is_idempotent(self):
        old = event(
            "fb0847fb538e", title="Impact Onchain: from hackathon to real projects",
            start="2026-11-04T11:00:00+01:00", end="2026-11-04T12:30:00+01:00",
            online=True, place="Online", city=None, country="SE",
            url="https://events.kaupr.io/products/impact-onchain",
        )
        moved = dict(old, start="2026-11-11T11:00:00+01:00", end="2026-11-11T12:30:00+01:00", status="published")
        other = event("43e778cb5318", title="Bitcoin Suisse Europe launches in the Nordics", start="2026-11-19T17:30:00+01:00", end=None, status="published")
        root = self.root([old])
        d1_store.sync_root(self.store, root, AT, require_verified=True)
        d1_store.save_json(os.path.join(root, "data", "events.json"), {"events": [moved, other]})
        first = d1_store.seed_events(self.store, root, ("fb0847fb538e", "43e778cb5318"), ("impact onchain", "2026-11-04"))
        self.assertEqual(first["updated"], 1)
        self.assertEqual(first["inserted"], 1)
        row = json.loads(d1_store.one(self.store, "SELECT payload, review_status FROM events WHERE id = 'fb0847fb538e'")["payload"])
        self.assertTrue(row["start"].startswith("2026-11-11"))
        self.assertEqual(d1_store.one(self.store, "SELECT review_status FROM events WHERE id = 'fb0847fb538e'")["review_status"], "approved")
        second = d1_store.seed_events(self.store, root, ("fb0847fb538e", "43e778cb5318"), ("impact onchain", "2026-11-04"))
        self.assertEqual(second["inserted"] + second["updated"], 0)
        self.assertEqual(len(self.store.query("SELECT id FROM events")), 2)


if __name__ == "__main__":
    unittest.main()
