#!/usr/bin/env python3
"""tools/x_feed.py: mirror Telegram digests/events on X. No network."""
import datetime as dt, json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import x_feed as xf

NOW = dt.datetime(2026, 11, 5, 7, 30, tzinfo=dt.timezone.utc)  # 08:30 Oslo


def ev(i, start, end=None, **kw):
    e = {"id": i, "title": f"Meetup {i}", "start": start, "end": end, "place": "Ölrepubliken, Kronhusgatan 2B",
         "city": "Göteborg", "country": "SE", "organiser": "Swedish Bitcoin Meetups",
         "html_url": f"https://nordiccrypto.no/calendar/{i}/"}
    e.update(kw)
    return e


def story(i, published, **kw):
    e = {"id": i, "published": published, "country": "NO", "title": f"Sak {i}", "title_en": f"Story {i}",
         "language_code": "en", "source_name": "E24",
         "html_url": f"https://nordiccrypto.no/stories/{i}/"}
    e.update(kw)
    return e


class Poster:
    def __init__(self, fail_on=()):
        self.sent, self.fail_on = [], set(fail_on)

    def __call__(self, creds, text, reply_to=None):
        if any(f in text for f in self.fail_on):
            raise RuntimeError("X API 400")
        self.sent.append(text)
        return str(1000 + len(self.sent))


class XFeed(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ledger = os.path.join(self.dir, "ledger.json")
        self.log = []
        self.poster = Poster()
        from unittest import mock
        p = mock.patch.object(xf.time, "sleep"); p.start(); self.addCleanup(p.stop)

    def go(self, payload, *, kind="events", dry=False, force=(), max_posts=5):
        return xf.run(payload, self.ledger, now=NOW, creds=("k",) * 4, max_posts=max_posts, dry=dry,
                      kind=kind, force=list(force), poster=self.poster, log_fn=self.log.append)

    def ids(self):
        return json.load(open(self.ledger))["posted"]

    def test_first_run_seeds_events_and_posts_nothing(self):
        self.assertEqual(self.go({"events": [ev("a1", "2026-11-12T18:00:00+01:00")]}), 0)
        self.assertEqual(self.poster.sent, [])
        self.assertEqual(self.ids(), ["a1"])

    def test_posts_new_event_once(self):
        self.go({"events": [ev("a1", "2026-11-12T18:00:00+01:00")]})
        self.go({"events": [ev("a1", "2026-11-12T18:00:00+01:00"),
                            ev("b2", "2026-11-12T18:00:00+01:00", title="Göteborg Bitcoin Meetup #50")]})
        self.assertEqual(len(self.poster.sent), 1)
        t = self.poster.sent[0]
        self.assertIn("📅 New event: Göteborg Bitcoin Meetup #50", t)
        self.assertIn("🗓 Thu 12 Nov 2026, 18:00", t)
        self.assertIn("📍 🇸🇪 Ölrepubliken, Kronhusgatan 2B, Göteborg", t)
        self.assertIn("👥 Swedish Bitcoin Meetups", t)
        self.assertIn("https://nordiccrypto.no/calendar/b2/", t)
        self.assertNotIn("phone", t.lower())
        self.assertNotIn("jQrgen", t)
        self.assertNotIn("Nordic Crypto AS", t)
        self.go({"events": [ev("a1", "2026-11-12T18:00:00+01:00"), ev("b2", "2026-11-12T18:00:00+01:00")]})
        self.assertEqual(len(self.poster.sent), 1)

    def test_news_digest_with_source_and_links(self):
        self.go({"items": [], "updated": "2026-11-05T06:00:00+00:00"}, kind="news")
        items = [story("virtune", "2026-11-04T12:00:00+00:00", country="SE",
                       title_en="Virtune AI crypto index ETP", source_name="Kaupr"),
                 story("firi", "2026-11-04T15:55:37+00:00",
                       title_en="Firi trading doubled after Binance hack", source_name="E24")]
        self.assertEqual(self.go({"items": items, "updated": "2026-11-05T06:00:00+00:00"}, kind="news"), 0)
        self.assertEqual(len(self.poster.sent), 1)
        t = self.poster.sent[0]
        self.assertTrue(t.startswith("📰 New stories on Nordic Crypto – 5.11.2026"))
        self.assertIn("Virtune AI crypto index ETP – Source: Kaupr", t)
        self.assertIn("https://nordiccrypto.no/stories/virtune/", t)
        self.assertIn("Firi trading doubled after Binance hack – Source: E24", t)
        self.assertIn("https://nordiccrypto.no/stories/firi/", t)

    def test_news_settle_window(self):
        self.go({"items": [], "updated": "2026-11-05T06:00:00+00:00"}, kind="news")
        items = [story("a", "2026-11-05T07:25:00+00:00")]
        self.assertEqual(self.go({"items": items, "updated": "2026-11-05T07:25:00+00:00"}, kind="news"), 0)
        self.assertEqual(self.poster.sent, [])

    def test_backfill_news_ids(self):
        items = [story("old", "2026-11-01T12:00:00+00:00"), story("a", "2026-11-04T12:00:00+00:00")]
        self.go({"items": items, "updated": "2026-11-05T06:00:00+00:00"}, kind="news")
        self.go({"items": items, "updated": "2026-11-05T06:00:00+00:00"}, kind="news")
        self.assertEqual(self.poster.sent, [])  # seeded
        self.go({"items": items, "updated": "2026-11-05T06:00:00+00:00"}, kind="news", force=["old"])
        self.assertEqual(len(self.poster.sent), 1)
        self.assertIn("stories/old/", self.poster.sent[0])

    def test_backfill_event_ids(self):
        self.go({"events": [ev("a1", "2026-11-12T18:00:00+01:00")]})
        self.go({"events": [ev("a1", "2026-11-12T18:00:00+01:00")]}, force=["a1"])
        self.assertEqual(len(self.poster.sent), 1)
        self.assertIn("calendar/a1/", self.poster.sent[0])

    def test_dry_run_and_missing_creds(self):
        self.go({"events": []})
        self.go({"events": [ev("d1", "2026-11-12T18:00:00+01:00")]}, dry=True)
        self.assertEqual(self.poster.sent, [])
        self.assertEqual(self.ids(), [])
        code = xf.run({"events": [ev("d1", "2026-11-12T18:00:00+01:00")]}, self.ledger, now=NOW,
                      creds=None, max_posts=5, dry=False, poster=self.poster, log_fn=self.log.append)
        self.assertEqual(code, 0)
        self.assertEqual(self.poster.sent, [])

    def test_preview_refused(self):
        self.assertEqual(self.go({"preview": True, "events": []}), 2)

    def test_news_reuses_the_stored_image(self):
        self.go({"items": [], "updated": "2026-11-05T06:00:00+00:00"}, kind="news")
        seen = {}

        def poster(creds, text, reply_to=None, media_ids=None):
            seen["media"] = list(media_ids or [])
            return "55"

        def fetcher(url):
            seen.setdefault("urls", []).append(url)
            path = os.path.join(self.dir, "pic.png")
            with open(path, "wb") as fh:
                fh.write(b"\x89PNG" + b"x" * 40)
            return path

        item = story("virtune", "2026-11-04T12:00:00+00:00",
                     image={"url": "https://api.nordiccrypto.no/story-images/virtune.png", "kind": "original"})
        code = xf.run({"items": [item], "updated": "2026-11-05T06:00:00+00:00"}, self.ledger,
                      now=NOW, creds=("k",) * 4, max_posts=5, dry=False, kind="news", poster=poster,
                      log_fn=self.log.append, image_fetcher=fetcher, image_uploader=lambda creds, path: "media-1")
        self.assertEqual(code, 0)
        self.assertEqual(seen["urls"], ["https://api.nordiccrypto.no/story-images/virtune.png"])
        self.assertEqual(seen["media"], ["media-1"])

    def test_failed_send_not_recorded(self):
        self.go({"events": []})
        self.poster = Poster(fail_on=["Meetup x2"])
        self.assertEqual(self.go({"events": [ev("x2", "2026-11-12T18:00:00+01:00")]}), 1)
        self.assertEqual(self.ids(), [])


if __name__ == "__main__":
    unittest.main()
