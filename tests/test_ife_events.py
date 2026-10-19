#!/usr/bin/env python3
"""IFE (WordPress event posts) intake. No network. Does not write data/events.json."""
import datetime as dt
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import events

SRC = {"id": "ife-events", "name": "IFE – events", "country": "NO", "url": "https://ife.no/en/",
       "api": "https://ife.no/wp-json/wp/v2/event", "type": "wp-event-pages", "trusted": False,
       "organiser": "Institute for Energy Technology (IFE)", "keywords": ["bitcoin", "blockchain", "digital sovereignty"]}
ICDS = "https://ife.no/en/event/international-conference-on-digital-sovereignty-icds-2026/"
RECORDS = [
    {"link": ICDS, "title": {"rendered": "3rd International Conference on Digital Sovereignty (ICDS) 2026"},
     "content": {"rendered": "<h1>Welcome to ICDS 2026!</h1><p>It is with great pleasure to welcome you to the Third "
                             "International Conference on Digital Sovereignty (ICDS 2026), in Oslo, <strong>Norway</strong>.</p>"
                             "<h2>Conference program</h2><p>Flip-book.</p>"}},
    {"link": "https://ife.no/event/arendalsuka-2026/", "title": {"rendered": "Arendalsuka 2026"},
     "content": {"rendered": "<p>IFE på Arendalsuka.</p>"}},
]
PAGES = {ICDS: """<div class="sidebar__content">
<p class="single-event-block__extra-info"><b>From: </b>25. November 2026 09:00</p>
<p class="single-event-block__extra-info"><b>Until: </b>27. November 2026 16:00</p>
<p class="single-event-block__extra-info"><b>Location: </b>Oslo Science Park, Oslo, Norway</p></div>"""}
NOW = dt.datetime(2026, 10, 19, 11, 0, tzinfo=dt.timezone.utc)


class IfeTest(unittest.TestCase):
    def test_keyword_hit_with_page_dates_and_place(self):
        opened = []
        evs = events.wp_event_pages(SRC, RECORDS, "Europe/Oslo", lambda u: opened.append(u) or PAGES[u], NOW)
        self.assertEqual(opened, [ICDS])
        self.assertEqual(len(evs), 1)
        e = evs[0]
        self.assertEqual(e["start"].isoformat(), "2026-11-25T09:00:00+01:00")
        self.assertEqual(e["end"].isoformat(), "2026-11-27T16:00:00+01:00")
        self.assertEqual(e["place"], "Oslo Science Park, Oslo")
        self.assertEqual(e["country_hint"], "NO")
        self.assertTrue(e["description"].endswith("in Oslo, Norway."))
        self.assertTrue(events.source_keeps(e, SRC, False, lambda t: []))

    def test_norwegian_labels_and_date_only(self):
        html = ('<p class="single-event-block__extra-info"><b>Fra: </b>25. september 2026</p>'
                '<p class="single-event-block__extra-info"><b>Lokasjon: </b>Deichman Bjørvika</p>')
        f = events.wp_event_page(html, "Europe/Oslo")
        self.assertEqual(f["start"].isoformat(), "2026-09-25T00:00:00+02:00")
        self.assertIsNone(f["end"])
        self.assertEqual(f["place"], "Deichman Bjørvika")

    def test_past_event_dropped(self):
        later = dt.datetime(2026, 12, 1, tzinfo=dt.timezone.utc)
        self.assertEqual(events.wp_event_pages(SRC, RECORDS, "Europe/Oslo", PAGES.get, later), [])


if __name__ == "__main__":
    unittest.main()
