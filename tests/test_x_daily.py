import datetime as dt, io, json, os, sys, tempfile, unittest, contextlib
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import x_daily as xd

NOW = dt.datetime(2026, 10, 18, 5, 37, tzinfo=dt.timezone.utc)  # 07:37 Oslo


FULL = {l: "x" for l in xd.headlines.TRANSLATED}


def story(i, published, **kw):
    return dict({"id": i, "published": published, "country": "SE", "language": "Swedish", "title": f"Sak {i}",
                 "title_en": f"Story {i}", "title_i18n": FULL, "summary": "S.", "summary_i18n": FULL}, **kw)


class Digest(unittest.TestCase):
    def setUp(self):
        self.state = os.path.join(tempfile.mkdtemp(), "x_daily.json")
        self.sent, self.live = [], set()
        p = mock.patch.object(xd.time, "sleep"); p.start(); self.addCleanup(p.stop)

    def poster(self, creds, text, reply_to=None):
        self.sent.append((text, reply_to)); return str(100 + len(self.sent))

    def go(self, items, now=NOW, **kw):
        return xd.run({"items": items}, self.state, now, dry=False, creds=("k",) * 4, poster=self.poster,
                      live=lambda u: u not in self.live, **kw)

    def test_one_post_today_only(self):
        self.go([story("old", "2026-10-17T21:00:00+00:00"), story("a", "2026-10-18T03:00:00+00:00", country="NO"),
                 story("b", "2026-10-18T04:00:00+00:00", title_en=None, title_i18n=dict(FULL, en="English b"))])
        self.assertEqual(self.sent, [("📰 New on Nordic Crypto – 18 Oct 2026\n\n"
                                      "🇳🇴 Story a\nhttps://nordiccrypto.no/stories/a/\n\n"
                                      "🇸🇪 English b\nhttps://nordiccrypto.no/stories/b/", None)])
        st = json.load(open(self.state))["2026-10-18"]
        self.assertEqual((st["story_ids"], st["tweet_ids"], st["complete"]), (["a", "b"], ["101"], True))

    def test_never_twice_and_next_day_only_new(self):
        items = [story("a", "2026-10-18T03:00:00+00:00")]
        self.go(items); self.go(items + [story("late", "2026-10-18T06:00:00+00:00")], NOW + dt.timedelta(hours=2))
        self.assertEqual(len(self.sent), 1)
        self.go(items + [story("late", "2026-10-18T06:00:00+00:00")], NOW + dt.timedelta(days=1))
        self.assertEqual(len(self.sent), 2)
        self.assertIn("stories/late/", self.sent[1][0]); self.assertNotIn("stories/a/", self.sent[1][0])
        self.assertTrue(self.sent[1][0].startswith("📰 New on Nordic Crypto – 19 Oct 2026"))

    def test_nothing_new_posts_nothing(self):
        self.go([story("old", "2026-10-16T07:00:00+00:00")])
        self.assertEqual(self.sent, []); self.assertFalse(os.path.exists(self.state))

    def test_thread_when_too_long(self):
        items = [story(f"s{n:02}", f"2026-10-18T0{n % 5}:{n:02}:00+00:00", title_en="A fairly long English headline " * 3)
                 for n in range(9)]
        self.go(items)
        self.assertGreater(len(self.sent), 1)
        self.assertEqual([r for _, r in self.sent], [None] + [str(101 + i) for i in range(len(self.sent) - 1)])
        text = "\n".join(t for t, _ in self.sent)
        for e in items:
            self.assertIn(f"https://nordiccrypto.no/stories/{e['id']}/", text)
        for t, _ in self.sent:
            self.assertLessEqual(xd.weight(t), 280)
            self.assertNotIn("Crypto Nordic", t)

    def test_resumes_broken_thread(self):
        items = [story(f"s{n}", f"2026-10-18T0{n}:00:00+00:00", title_en="Headline words " * 8) for n in range(6)]
        posts = xd.build_posts(items, NOW.astimezone(xd.te.OSLO))
        xd.xn.save_state(self.state, {"2026-10-18": {"story_ids": [e["id"] for e in items], "tweet_ids": ["9"], "complete": False}})
        self.go(items)
        self.assertEqual([t for t, _ in self.sent], posts[1:]); self.assertEqual(self.sent[0][1], "9")

    def test_waits_for_translation_and_live_page(self):
        a = story("a", "2026-10-18T05:00:00+00:00")
        b = story("b", "2026-10-18T05:10:00+00:00", title_i18n={k: v for k, v in FULL.items() if k != "de"})
        self.live.add("https://nordiccrypto.no/stories/a/")
        self.go([a, b]); self.assertEqual(self.sent, [])
        self.live.clear(); self.go([a, b]); self.assertEqual(self.sent, [])
        b["title_i18n"] = FULL; self.go([a, b])
        self.assertEqual(len(self.sent), 1); self.assertIn("stories/b/", self.sent[0][0])

    def test_source_language_headline_not_needed(self):
        self.go([story("a", "2026-10-18T05:00:00+00:00", title_i18n={k: v for k, v in FULL.items() if k != "sv"})])
        self.assertEqual(len(self.sent), 1)

    def test_deadline_posts_ready_and_late_story_stops_blocking(self):
        a, b = story("a", "2026-10-18T05:00:00+00:00"), story("b", "2026-10-18T05:10:00+00:00", summary_i18n={})
        self.go([a, b], NOW.replace(hour=15)); self.assertEqual(self.sent, [])
        self.go([a, b], NOW.replace(hour=16))  # 18:07 Oslo
        self.assertEqual(len(self.sent), 1); self.assertNotIn("stories/b/", self.sent[0][0])
        c = story("c", "2026-10-19T05:00:00+00:00")
        self.go([a, b, c], NOW + dt.timedelta(days=1, minutes=30))  # 08:07 Oslo next day
        self.assertEqual(len(self.sent), 2); self.assertIn("stories/c/", self.sent[1][0]); self.assertNotIn("stories/b/", self.sent[1][0])

    def test_preview_refused(self):
        self.assertEqual(xd.run({"preview": True, "items": []}, self.state, NOW, dry=False, creds=None), 2)
        self.assertEqual(self.sent, [])

    def test_dry_run_and_missing_secrets_post_nothing(self):
        items = {"items": [story("a", "2026-10-18T03:00:00+00:00")]}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            xd.run(items, self.state, NOW, dry=True, poster=self.poster, live=lambda u: True)
        self.assertIn("📰 New on Nordic Crypto – 18 Oct 2026", out.getvalue())
        xd.run(items, self.state, NOW, dry=False, creds=None, poster=self.poster, live=lambda u: True)
        self.assertEqual(self.sent, []); self.assertFalse(os.path.exists(self.state))

    def test_weight(self):
        self.assertEqual(xd.weight("ab https://nordiccrypto.no/stories/" + "x" * 50 + "/"), 3 + 23)
        self.assertEqual(xd.weight("📰"), 2)


if __name__ == "__main__":
    unittest.main()
