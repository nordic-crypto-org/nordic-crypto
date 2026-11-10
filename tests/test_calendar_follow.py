"""The calendar page has one Follow calendar menu, and the ICS feed is valid.

New copy must not add a digit run the privacy gate treats as a phone number.
The existing day-length literal in the live calendar script is left for the
other change that rewrites it.
"""
import html
import os
import sys
import tempfile
import unittest
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import build
import i18n
from tools import event_ics
from tools.privacy_gate import RULES

PHONE = RULES["telefonnummer"]
FEED = "https://nordiccrypto.no/calendar.ics"
GCAL = "https://calendar.google.com/calendar/r?cid=https%3A%2F%2Fnordiccrypto.no%2Fcalendar.ics"
APPLE = "webcal://nordiccrypto.no/calendar.ics"
OUTLOOK = "https://outlook.live.com/calendar/0/addfromweb?url=https%3A%2F%2Fnordiccrypto.no%2Fcalendar.ics&name=Nordic%20Crypto"
M365 = "https://outlook.office.com/calendar/0/addfromweb?url=https%3A%2F%2Fnordiccrypto.no%2Fcalendar.ics&name=Nordic%20Crypto"
LABELS = ("cal_follow", "cal_gcal", "cal_apple", "cal_outlook", "cal_m365", "cal_copy", "cal_copied", "cal_apps")


def row():
    return {
        "id": "x", "title": "Meetup", "start": "2026-11-12T18:00:00+01:00",
        "place": "Hall", "city": "Oslo", "country": "NO", "organiser": "Org",
        "url": "https://example.org/e", "source": "Src", "status": "published",
    }


def unfold(text):
    return text.replace("\r\n ", "").replace("\r\n\t", "")


class FollowButton(unittest.TestCase):
    def page(self, lang):
        from tools import event_select
        now = event_select.clock("2026-11-09T12:00:00+01:00")
        saved = build.SITE, build.PREVIEW, build.LANG
        try:
            with tempfile.TemporaryDirectory() as site:
                build.SITE, build.PREVIEW, build.LANG = site, False, lang
                build.build_calendar({"events": ([row()], now)})
                path = os.path.join(site, "" if lang == "en" else lang, "calendar", "index.html")
                with open(path, encoding="utf-8") as fh:
                    return fh.read()
        finally:
            build.SITE, build.PREVIEW, build.LANG = saved

    def test_subscribe_urls_use_the_one_https_feed(self):
        self.assertEqual(build.calendar_feed_url(), FEED)
        self.assertEqual(build.google_calendar_href(), GCAL)
        self.assertEqual(build.apple_calendar_href(), APPLE)
        self.assertEqual(build.outlook_calendar_href("outlook.live.com"), OUTLOOK)
        self.assertEqual(build.outlook_calendar_href("outlook.office.com"), M365)
        for href in (GCAL, APPLE, OUTLOOK, M365, FEED):
            self.assertIsNone(PHONE.search(href), href)
            self.assertEqual(urllib.parse.unquote(href).count("nordiccrypto.no/calendar.ics"), 1)

    def test_one_menu_in_every_language(self):
        for lang in i18n.ALL_LANGS:
            page = self.page(lang)
            self.assertEqual(page.count('class="cal-follow"'), 1, lang)
            summary = html.escape(i18n.t(lang, "cal_follow"), quote=True)
            self.assertIn("<summary>" + summary + "</summary>", page, lang)
            for key in LABELS:
                self.assertTrue(i18n.has(lang, key), (lang, key))
                label = i18n.t(lang, key)
                self.assertNotEqual(label, "", (lang, key))
                self.assertIsNone(PHONE.search(label), (lang, key))
                self.assertIn(html.escape(label, quote=True), page, lang)
            # Real anchors, so the menu works with no JavaScript. One feed only.
            for href in (GCAL, APPLE, OUTLOOK, M365, FEED):
                needle = 'href="' + html.escape(href, quote=True) + '"'
                self.assertEqual(page.count(needle), 1, (lang, href))
            self.assertIn('class="cal-copy"', page, lang)
            self.assertIn('data-url="' + FEED + '"', page, lang)
            self.assertIn('class="cal-feed-url"', page, lang)
            self.assertIn('key!=="Escape"', page, lang)
            self.assertIn("navigator.clipboard", page, lang)
            self.assertNotIn(">iCal<", page, lang)
            found = [m.group(0) for line in page.splitlines() for m in PHONE.finditer(line)]
            self.assertTrue(all(hit == "86400000" for hit in found), (lang, found))


class IcsFeed(unittest.TestCase):
    def assert_rfc(self, body):
        self.assertTrue(body.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"))
        self.assertTrue(body.endswith("END:VCALENDAR\r\n"))
        self.assertNotIn("\n", body.replace("\r\n", ""))
        self.assertNotIn("\r\n\r\n", body)
        for line in body.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75, line)
        flat = unfold(body)
        self.assertIn("PRODID:-//Nordic Crypto//Calendar//EN", flat)
        self.assertIn("CALSCALE:GREGORIAN", flat)
        self.assertIn("METHOD:PUBLISH", flat)
        self.assertEqual(flat.count("BEGIN:VCALENDAR"), flat.count("END:VCALENDAR"))
        self.assertEqual(flat.count("BEGIN:VEVENT"), flat.count("END:VEVENT"))

    def test_empty_calendar_is_still_valid(self):
        body = event_ics.render([], now="2026-11-09T12:00:00+00:00")
        self.assert_rfc(body)
        self.assertNotIn("BEGIN:VEVENT", body)

    def test_map_url_goes_in_the_description_when_there_is_an_address(self):
        link = "https://www.google.com/maps/search/?api=1&query=Sturegatan%2015,Stockholm"
        body = event_ics.render([
            {
                "id": "ab", "title": "Møte, Oslo", "start": "2026-11-19T18:00:00+01:00",
                "end": "2026-11-19T19:15:00+01:00",
                "place": "Sturegatan 15", "city": "Stockholm", "online": False,
                "url": "https://example.org/e", "map_url": link,
                "note": "Write a@b.co or call +47 22 33 44 55",
            },
        ], now="2026-11-09T12:00:00+00:00")
        self.assert_rfc(body)
        flat = unfold(body)
        self.assertIn("UID:ab@nordiccrypto.no", flat)
        self.assertIn("DTSTAMP:20261109T120000Z", flat)
        self.assertIn("DTSTART:20261119T170000Z", flat)
        self.assertIn("DTEND:20261119T181500Z", flat)
        self.assertIn("SUMMARY:Møte\\, Oslo", flat)
        self.assertIn("LOCATION:Sturegatan 15\\, Stockholm", flat)
        self.assertIn("DESCRIPTION:Write or call\\n" + link.replace(",", "\\,"), flat)
        self.assertNotIn("a@b.co", flat)
        self.assertNotIn("22 33 44 55", flat)
        self.assertNotIn("jQrgen", flat)

    def test_map_url_is_the_location_when_there_is_no_address(self):
        link = "https://www.google.com/maps/search/?api=1&query=Online"
        body = event_ics.render([
            {"id": "on", "title": "Pinned", "start": "2026-11-19T18:00:00+01:00", "map_url": link},
        ], now="2026-11-09T12:00:00+00:00")
        self.assert_rfc(body)
        flat = unfold(body)
        self.assertIn("LOCATION:" + link, flat)
        self.assertNotIn("DESCRIPTION:", flat)

    def test_fold_keeps_an_escape_together(self):
        title = "A, " * 40
        body = event_ics.render([
            {"id": "long", "title": title.strip(), "start": "2026-11-19T18:00:00+01:00"},
        ], now="2026-11-09T12:00:00+00:00")
        self.assert_rfc(body)
        flat = unfold(body)
        self.assertIn("SUMMARY:" + event_ics._escape(title.strip()), flat)
        for line in body.split("\r\n"):
            self.assertFalse(line.endswith("\\"))


if __name__ == "__main__":
    unittest.main()
