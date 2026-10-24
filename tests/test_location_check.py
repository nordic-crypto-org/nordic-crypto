#!/usr/bin/env python3
"""Event locations: a physical event row needs a street address or coordinates. No network."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools import event_page, location_check as lc


class LocationCheck(unittest.TestCase):
    def test_rules(self):
        self.assertIsNotNone(lc.issue({"place": "Vingtor", "city": "Stavanger"}))
        self.assertIsNone(lc.issue({"place": "Vingtor, Børehaugen 1A, 4006 Stavanger", "city": "Stavanger"}))
        self.assertIsNone(lc.issue({"place": "Oslo", "city": "Oslo"}))
        self.assertIsNone(lc.issue({"place": "Online (YouTube)", "online": True}))
        self.assertIsNone(lc.issue({"place": "Vingtor", "city": "Stavanger", "lat": 58.97, "lng": 5.73}))

    def test_known_venue_gets_street(self):
        self.assertEqual(lc.with_address("Vingtor", "Stavanger"), "Vingtor, Børehaugen 1A, 4006 Stavanger")
        self.assertEqual(lc.with_address("Vingtor", "Oslo"), "Vingtor")
        q = event_page.map_url({"place": lc.with_address("Vingtor", "Stavanger"), "city": "Stavanger", "country": "NO"})
        self.assertIn("B%C3%B8rehaugen%201A", q)

    def test_stored_events(self):
        for f in ("data/events.json", "archive/events.json"):
            for e in json.load(open(os.path.join(ROOT, f), encoding="utf-8"))["events"]:
                self.assertIsNone(lc.issue(e), f"{f} {e.get('id')}")


if __name__ == "__main__":
    unittest.main()
