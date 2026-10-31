"""A multi-day event shows on every day it spans in the month grid, and is still counted once."""
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build
from tools import event_select


def row(id_, start, end=None):
    e = {"id": id_, "title": id_, "start": start, "place": "Venue", "city": "Oslo", "country": "NO",
         "organiser": "Test", "url": "https://example.test/" + id_, "source": "Test", "status": "published"}
    if end:
        e["end"] = end
    return e


class CalendarGrid(unittest.TestCase):
    def days(self, lang, rows):
        now = event_select.clock("2026-11-02T12:00:00+01:00")
        saved = build.SITE, build.PREVIEW, build.LANG
        try:
            with tempfile.TemporaryDirectory() as site:
                build.SITE, build.PREVIEW, build.LANG = site, False, lang
                build.build_calendar({"events": (rows, now)})
                with open(os.path.join(site, "" if lang == "en" else lang, "calendar", "index.html"), encoding="utf-8") as fh:
                    html = fh.read()
        finally:
            build.SITE, build.PREVIEW, build.LANG = saved
        out = {}
        for table in re.findall(r'<table class="cal"><caption>(.*?)</caption>(.*?)</table>', html, re.S):
            for cls, day, cell in re.findall(r'<td class="([^"]*)"><span class="d">(\d+)</span>(.*?)</td>', table[1], re.S):
                for id_ in re.findall(r'<a href="([^"/]+)/"', cell):
                    out.setdefault(id_, []).append((table[0], int(day), "out" in cls))
        return html, out

    def test_spans_every_day(self):
        rows = [row("multi", "2026-11-25T09:00:00+01:00", "2026-11-27T16:00:00+01:00"),
                row("midnight", "2026-11-10T18:00:00+01:00", "2026-11-11T00:00:00+01:00"),
                row("spill", "2026-11-29T10:00:00+01:00", "2026-12-01T12:00:00+01:00"),
                row("noend", "2026-11-12T22:00:00+01:00")]
        for lang in ("nb", "en"):
            html, days = self.days(lang, rows)
            nov = days["multi"][0][0]
            self.assertEqual([(d, o) for c, d, o in days["multi"] if c == nov], [(25, False), (26, False), (27, False)])
            self.assertEqual([d for c, d, o in days["midnight"]], [10])
            self.assertEqual([d for c, d, o in days["noend"]], [12])
            self.assertEqual([(d, o) for c, d, o in days["spill"] if c == nov], [(29, False), (30, False), (1, True)])
            self.assertEqual(html.count('id="e-multi"'), 1)
            self.assertIn(": 4", html)


if __name__ == "__main__":
    unittest.main()
