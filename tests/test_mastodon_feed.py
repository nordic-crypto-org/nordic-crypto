#!/usr/bin/env python3
"""tools/mastodon_feed.py: mirror the X events/news feed on Mastodon. No network."""
import datetime as dt, json, os, sys, tempfile, unittest, urllib.error
from unittest import mock
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import mastodon_feed as mf

NOW = dt.datetime(2026, 11, 5, 7, 30, tzinfo=dt.timezone.utc)
UPDATED = "2026-11-05T06:00:00+00:00"


def ev(i, start="2026-11-12T18:00:00+01:00", **kw):
    e = {"id": i, "title": f"Meetup {i}", "start": start, "place": "Ölrepubliken", "city": "Göteborg",
         "country": "SE", "organiser": "Swedish Bitcoin Meetups", "html_url": f"https://nordiccrypto.no/calendar/{i}/"}
    e.update(kw)
    return e


def story(i, published="2026-11-04T12:00:00+00:00", **kw):
    e = {"id": i, "published": published, "country": "NO", "title_en": f"Story {i}", "language_code": "en",
         "source_name": "E24", "html_url": f"https://nordiccrypto.no/stories/{i}/"}
    e.update(kw)
    return e


class Poster:
    def __init__(self, fail_at=None, code=500):
        self.sent, self.fail_at, self.code = [], fail_at, code

    def __call__(self, token, text, media_ids=None, reply_to=None):
        if self.fail_at is not None and len(self.sent) == self.fail_at:
            raise urllib.error.HTTPError("u", self.code, "err", {}, None)
        self.sent.append({"text": text, "media": media_ids, "reply_to": reply_to})
        sid = str(100 + len(self.sent))
        return sid, f"https://mastodon.social/@nordiccrypto/{sid}"


class MastodonFeed(unittest.TestCase):
    def setUp(self):
        self.ledger = os.path.join(tempfile.mkdtemp(), "ledger.json")
        self.log, self.uploads = [], []
        self.poster = Poster()
        p = mock.patch.object(mf.time, "sleep"); p.start(); self.addCleanup(p.stop)

    def render(self, item, path, *, kind="news", recent_styles=None, **kw):
        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\nfake")
        return "photoreal-editorial", path

    def upload(self, token, path):
        self.uploads.append(path)
        return f"m{len(self.uploads)}"

    def go(self, feed, *, kind="events", dry=False, force=(), token="t"):
        return mf.run(feed, self.ledger, now=NOW, token=token, max_posts=5, dry=dry, kind=kind, force=list(force),
                      poster=self.poster, uploader=self.upload, image_renderer=self.render,
                      image_fetcher=lambda url: None, log_fn=self.log.append)

    def posted(self):
        with open(self.ledger) as fh:
            return json.load(fh)["posted"]

    def test_first_run_seeds_and_posts_nothing(self):
        self.assertEqual(self.go({"events": [ev("a")]}), 0)
        self.assertEqual((self.poster.sent, self.posted()), ([], ["a"]))

    def test_new_event_posted_once_with_link_and_image(self):
        self.go({"events": [ev("a")]})
        self.go({"events": [ev("a"), ev("b")]})
        self.go({"events": [ev("a"), ev("b")]})
        self.assertEqual(len(self.poster.sent), 1)
        p = self.poster.sent[0]
        self.assertIn("📅 New event: Meetup b", p["text"])
        self.assertIn("https://nordiccrypto.no/calendar/b/", p["text"])
        self.assertEqual(p["media"], ["m1"])
        self.assertLessEqual(mf.m_len(p["text"]), 500)

    def test_long_event_title_is_shortened_to_fit(self):
        self.go({"events": []})
        self.go({"events": [ev("x", title="Bitcoin " * 100)]})
        t = self.poster.sent[0]["text"]
        self.assertLessEqual(mf.m_len(t), 500)
        self.assertIn("https://nordiccrypto.no/calendar/x/", t)

    def test_news_digest_threads_when_over_500(self):
        self.go({"items": [], "updated": UPDATED}, kind="news")
        items = [story(f"s{i}", title_en=f"A fairly long headline about Nordic crypto markets number {i}") for i in range(8)]
        self.go({"items": items, "updated": UPDATED}, kind="news")
        sent = self.poster.sent
        self.assertGreater(len(sent), 1)
        self.assertTrue(sent[0]["text"].startswith("📰 New stories on Nordic Crypto"))
        self.assertEqual(sent[0]["media"], ["m1"])
        self.assertEqual([p["reply_to"] for p in sent[1:]], [str(101 + i) for i in range(len(sent) - 1)])
        self.assertTrue(all(mf.m_len(p["text"]) <= 500 for p in sent))
        body = "\n".join(p["text"] for p in sent)
        for i in range(8):
            self.assertIn(f"https://nordiccrypto.no/stories/s{i}/", body)
        self.assertEqual(sorted(self.posted()), sorted(f"s{i}" for i in range(8)))

    def test_news_uses_stored_images(self):
        self.go({"items": [], "updated": UPDATED}, kind="news")
        items = [story("a", image={"url": "https://img.example/a.png"})]
        with mock.patch.object(mf.xf, "attach_story_images", return_value=["s1"]) as att:
            self.go({"items": items, "updated": UPDATED}, kind="news")
        att.assert_called_once()
        self.assertEqual(self.poster.sent[0]["media"], ["s1"])
        self.assertEqual(self.uploads, [])

    def test_failed_head_post_is_retried_next_run(self):
        self.go({"events": []})
        self.poster = Poster(fail_at=0, code=403)
        self.assertEqual(self.go({"events": [ev("a")]}), 1)
        self.assertEqual(self.posted(), [])
        self.assertTrue(any("write:statuses" in m for m in self.log))

    def test_dry_run_and_missing_token_post_nothing(self):
        self.go({"events": []})
        self.go({"events": [ev("a")]}, dry=True)
        self.go({"events": [ev("a")]}, token=None)
        self.assertEqual((self.poster.sent, self.posted()), ([], []))

    def test_backfill_and_preview(self):
        self.go({"events": [ev("a")]})
        self.go({"events": [ev("a")]}, force=["a"])
        self.assertEqual(len(self.poster.sent), 1)
        self.assertEqual(self.go({"preview": True, "events": []}), 2)

    def test_split_digest_keeps_blocks_whole(self):
        blocks = ["head"] + [f"🇳🇴 Title {i}\nhttps://nordiccrypto.no/stories/{i}/" for i in range(30)]
        parts = mf.split_digest("\n\n".join(blocks))
        self.assertEqual("\n\n".join(parts), "\n\n".join(blocks))
        self.assertTrue(all(mf.m_len(p) <= 500 for p in parts))


if __name__ == "__main__":
    unittest.main()
