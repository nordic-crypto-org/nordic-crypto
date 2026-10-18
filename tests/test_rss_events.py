#!/usr/bin/env python3
"""BIEN Norge events RSS: keyword filter and date/venue parser. No network."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import events

UTC = dt.timezone.utc
OSLO = "Europe/Oslo"
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "bien_norge_arrangementer.xml")
POST = "https://www.biennorge.no/what-happens-when-bitcoin-and-basic-income-meet/"


def src():
    cfg = json.load(open(os.path.join(ROOT, "sources.json"), encoding="utf-8"))
    return next(s for s in cfg["event_sources"] if s["id"] == "bien-norge-arrangementer")


def feed(title, body, pub="Mon, 07 Dec 2026 10:00:00 +0000"):
    return (f'<?xml version="1.0"?><rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>'
            f"<title>{title}</title><link>https://www.biennorge.no/x/</link><pubDate>{pub}</pubDate>"
            f"<content:encoded><![CDATA[<p>{body}</p>]]></content:encoded></item></channel></rss>")


class Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class RssEventsTests(unittest.TestCase):
    def test_fixture_item_before_the_day(self):
        evs = events.rss_events(src(), open(FIXTURE, encoding="utf-8").read(), OSLO, dt.datetime(2026, 9, 20, tzinfo=UTC))
        self.assertEqual(len(evs), 1)
        ev = evs[0]
        self.assertEqual(ev["title"], "Hva skjer når Bitcoin og borgerlønn møtes?")
        self.assertEqual(ev["start"].isoformat(), "2026-09-26T13:00:00+02:00")
        self.assertEqual(ev["end"].isoformat(), "2026-09-26T16:00:00+02:00")
        self.assertEqual((ev["place"], ev["city"]), ("Batteriet i Storggt. 32", "Oslo"))
        self.assertEqual(ev["organiser"], "BIEN Norge and Mission Possible 2030")
        self.assertEqual(ev["url"], POST)
        self.assertIs(ev["paid"], False)
        self.assertNotIn("dukket først opp", ev["description"])

    def test_past_item_is_skipped(self):
        evs = events.rss_events(src(), open(FIXTURE, encoding="utf-8").read(), OSLO, dt.datetime(2026, 10, 18, tzinfo=UTC))
        self.assertEqual(evs, [])

    def test_keyword_filter_drops_basic_income_only_posts(self):
        xml = feed("Borgerlønnsseminar", "Seminar på Litteraturhuset i Oslo den 12. januar kl. 18:00 – 20:00.")
        self.assertEqual(events.rss_events(src(), xml, OSLO, dt.datetime(2026, 12, 8, tzinfo=UTC)), [])

    def test_no_date_no_row(self):
        xml = feed("Bitcoin og borgerlønn", "Mer informasjon om bitcoin kommer.")
        self.assertEqual(events.rss_events(src(), xml, OSLO, dt.datetime(2026, 12, 8, tzinfo=UTC)), [])

    def test_missing_year_rolls_to_next_year_and_date_only_is_whole_day(self):
        xml = feed("Krypto-kveld", "Vi møtes på Kafé X i Bergen den 10. januar.")
        ev, = events.rss_events(src(), xml, OSLO, dt.datetime(2026, 12, 8, tzinfo=UTC))
        self.assertEqual(ev["start"].isoformat(), "2027-01-10T00:00:00+01:00")
        self.assertEqual(ev["end"].isoformat(), "2027-01-10T23:59:00+01:00")
        self.assertEqual((ev["place"], ev["city"]), ("Kafé X", "Bergen"))
        self.assertEqual(ev["organiser"], "BIEN Norge")

    def test_run_stores_a_pending_row(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "data"))
            json.dump({"events": []}, open(os.path.join(root, "data", "events.json"), "w", encoding="utf-8"))
            new = events.run(lambda u: Resp(open(FIXTURE, encoding="utf-8").read()), lambda u: True,
                             lambda t: "bitcoin" in t.lower(), lambda *a: None,
                             {"event_sources": [src()], "min_delay_seconds": 0, "user_agent": "test"},
                             root=root, now=dt.datetime(2026, 9, 20, tzinfo=UTC))
        self.assertEqual(len(new), 1)
        row = new[0]
        self.assertEqual((row["status"], row["country"], row["source_url"]), ("pending", "NO", POST))
        self.assertFalse(row["trusted_source"])


if __name__ == "__main__":
    unittest.main()
