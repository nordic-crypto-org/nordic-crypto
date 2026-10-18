import datetime as dt, json, os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import social_stories as ss

NOW = dt.datetime(2026, 10, 18, 5, 7, tzinfo=dt.timezone.utc)  # 07:07 Oslo
FULL = {l: "x" for l in ss.headlines.TRANSLATED}


def story(i, published, **kw):
    return dict({"id": i, "published": published, "country": "SE", "language": "Swedish", "title": f"Sak {i}",
                 "title_en": f"Story {i}", "title_i18n": FULL, "summary": "S.", "summary_i18n": FULL}, **kw)


class Fake:
    def __init__(self): self.sent = []
    def post(self, rec, reply_to=None):
        self.sent.append((rec, reply_to)); n = str(100 + len(self.sent))
        return (f"at://did/app.bsky.feed.post/{n}", f"https://bsky.app/profile/h/post/{n}") if isinstance(rec, dict) else n
    def permalink(self, i): return f"https://www.threads.com/@nordiccryptonews/post/{i}"


class Base(unittest.TestCase):
    def setUp(self):
        self.state = os.path.join(tempfile.mkdtemp(), "s.json"); self.c = Fake(); self.dead = set()
        p = mock.patch.object(ss.time, "sleep"); p.start(); self.addCleanup(p.stop)
        json.dump({"since": "2026-10-17T00:00:00+00:00"}, open(self.state, "w"))
    def live(self, u): return u not in self.dead


class Bluesky(Base):
    def go(self, items, now=NOW):
        return ss.run_bluesky({"items": items}, self.state, now, dry=False, client=self.c, live=self.live)

    def test_first_run_seeds_only(self):
        os.remove(self.state); self.go([story("a", "2026-10-18T04:00:00+00:00")])
        self.assertEqual(self.c.sent, []); self.assertEqual(json.load(open(self.state))["posted"], {})

    def test_one_post_per_story_with_link_card_once(self):
        items = [story("a", "2026-10-18T03:00:00+00:00", country="NO"), story("b", "2026-10-18T04:00:00+00:00")]
        self.go(items); self.go(items)
        self.assertEqual(len(self.c.sent), 2)
        rec = self.c.sent[0][0]; url = "https://nordiccrypto.no/stories/a/"
        self.assertEqual(rec["text"], f"🇳🇴 Story a\n{url}")
        f = rec["facets"][0]["index"]
        self.assertEqual(rec["text"].encode()[f["byteStart"]:f["byteEnd"]].decode(), url)
        self.assertEqual(rec["embed"]["external"]["uri"], url)
        self.assertEqual(set(json.load(open(self.state))["posted"]), {"a", "b"})

    def test_long_headline_fits(self):
        self.go([story("a", "2026-10-18T03:00:00+00:00", title_en="Very long English headline words " * 20)])
        t = self.c.sent[0][0]["text"]
        self.assertLessEqual(ss.bsky_len(t), 300); self.assertTrue(t.endswith("/stories/a/"))

    def test_waits_for_translation_and_page(self):
        a = story("a", "2026-10-18T04:00:00+00:00", summary_i18n={}); b = story("b", "2026-10-18T04:30:00+00:00")
        self.dead.add("https://nordiccrypto.no/stories/b/")
        self.go([a, b]); self.assertEqual(self.c.sent, [])
        self.go([a, b], NOW + dt.timedelta(hours=12)); self.assertEqual(len(self.c.sent), 1)  # a after the grace period


class Threads(Base):
    def go(self, items, now=NOW, **kw):
        return ss.run_threads({"items": items}, self.state, now, dry=False, client=self.c, live=self.live, **kw)

    def test_one_digest_per_day(self):
        items = [story("a", "2026-10-18T03:00:00+00:00", country="NO"), story("b", "2026-10-18T04:00:00+00:00")]
        self.go(items); self.go(items + [story("c", "2026-10-18T05:00:00+00:00")], NOW + dt.timedelta(minutes=30))
        self.assertEqual([t for t, _ in self.c.sent], ["📰 New on Nordic Crypto – 18 Oct 2026\n\n"
                         "🇳🇴 Story a\nhttps://nordiccrypto.no/stories/a/\n\n🇸🇪 Story b\nhttps://nordiccrypto.no/stories/b/"])
        self.go(items + [story("c", "2026-10-18T05:00:00+00:00")], NOW + dt.timedelta(days=1))
        self.assertEqual(len(self.c.sent), 2); self.assertIn("stories/c/", self.c.sent[1][0]); self.assertNotIn("stories/a/", self.c.sent[1][0])

    def test_thread_within_limits(self):
        items = [story(f"s{n}", f"2026-10-18T0{n % 5}:{n:02}:00+00:00", title_en="A fairly long English headline " * 3) for n in range(12)]
        self.go(items)
        self.assertGreater(len(self.c.sent), 1)
        self.assertEqual([r for _, r in self.c.sent], [None] + [str(101 + i) for i in range(len(self.c.sent) - 1)])
        for t, _ in self.c.sent:
            self.assertLessEqual(ss.threads_len(t), 500); self.assertLessEqual(len(ss.URL_RE.findall(t)), 5)
        self.assertTrue(json.load(open(self.state))["2026-10-18"]["complete"])

    def test_waits_then_deadline(self):
        a, b = story("a", "2026-10-18T04:00:00+00:00"), story("b", "2026-10-18T04:10:00+00:00", summary_i18n={})
        self.go([a, b]); self.assertEqual(self.c.sent, [])
        self.go([a, b], NOW.replace(hour=16)); self.assertEqual(len(self.c.sent), 1); self.assertNotIn("stories/b/", self.c.sent[0][0])


class Secrets(unittest.TestCase):
    def test_missing_secrets_skip(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(ss.te, "load_feed") as lf:
            self.assertEqual(ss.main(["threads", "--state", "/nonexistent/x.json"]), 0); lf.assert_not_called()

    def test_token_not_in_errors(self):
        err = ss.urllib.error.HTTPError("u", 400, "Bad", {}, None)
        err.read = lambda: b'{"error":"bad token SECRET123"}'
        with mock.patch.object(ss.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(RuntimeError) as cm: ss.Threads("1", "SECRET123").post("hi")
        self.assertNotIn("SECRET123", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
