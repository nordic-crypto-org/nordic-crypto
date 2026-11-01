#!/usr/bin/env python3
"""events.kaupr.io tip source: Lorem ipsum pages skipped, sitemap filter, config stays untrusted. No network."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import events


class KauprTipSource(unittest.TestCase):
    def test_lorem_page_skipped(self):
        self.assertFalse(events.tip_page_ok("<p>Lorem  ipsum dolor sit amet</p>"))
        self.assertTrue(events.tip_page_ok("<p>Impact Onchain</p>"))

    def test_sitemap_links(self):
        xml = "<loc>https://events.kaupr.io/products/a</loc><loc>https://events.kaupr.io/p/b</loc><loc>https://events.kaupr.io/products/a</loc>"
        self.assertEqual(events.tip_links(xml, "/products/", 10), ["https://events.kaupr.io/products/a"])

    def test_config_tip_only(self):
        cfg = json.load(open(os.path.join(ROOT, "sources.json"), encoding="utf-8"))
        for s in (x for x in cfg["event_sources"] if x["id"] in ("kaupr-events", "kaupr-events-tips")):
            self.assertTrue(s["tip_only"]); self.assertFalse(s["trusted"])

    def test_kaupr_never_sponsor(self):
        self.assertIsNone(events.clear_kaupr_sponsor("Kaupr"))


if __name__ == "__main__":
    unittest.main()
