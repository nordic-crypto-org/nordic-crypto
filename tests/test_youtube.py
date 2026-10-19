#!/usr/bin/env python3
"""YouTube templates and rule checks.  python3 -m unittest tests.test_youtube"""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import youtube_lint
import youtube_meta
import youtube_render
import youtube_video_upload

NOW = dt.datetime(2026, 10, 18, 18, 0, tzinfo=dt.timezone.utc)


def weekly(**kw):
    return youtube_meta.build("weekly", id="weekly-003", issue="003", number=3, headline="Test headline",
                              summary="The Nordic crypto news our editor approved.", day=dt.date(2026, 10, 19),
                              read_more="https://nordiccrypto.no/newsletter/003/", now=NOW, **kw)


def story():
    return youtube_meta.build("story", id="story-x", country="Sweden", headline="Riksbank asks for digital krona preparations",
                              summary="Two sentences.", read_more="https://nordiccrypto.no/stories/x/", day=dt.date(2026, 10, 20),
                              sources=[("Riksbank", "https://www.riksbank.se/")], hashtags=("#NordicCrypto", "#Sweden"), now=NOW)


class Templates(unittest.TestCase):
    def test_weekly(self):
        m = weekly()
        self.assertEqual(m["title"], "Nordic Crypto #3: Test headline")
        self.assertEqual(m["publishAt"], "2026-10-19T07:30:00Z")  # Mon 09:30 Oslo (CEST)
        self.assertTrue(m["containsSyntheticMedia"])
        self.assertEqual(youtube_lint.check(m), [])

    def test_short_hashtag_in_description_only(self):
        m = story()
        self.assertTrue(m["short"])
        self.assertNotIn("#Shorts", m["title"])
        self.assertIn("#Shorts", m["description"])
        self.assertIn("Sources: Riksbank – https://www.riksbank.se/", m["description"])
        self.assertEqual(youtube_lint.check(m), [])

    def test_publish_slot_after_dst_and_never_in_past(self):
        self.assertEqual(youtube_meta.publish_at("sixty", dt.date(2026, 10, 26), NOW), "2026-10-26T11:00:00Z")
        self.assertEqual(youtube_meta.publish_at("weekly", dt.date(2026, 10, 12), NOW), "2026-10-18T18:15:00Z")


class Lint(unittest.TestCase):
    def bad(self, **change):
        m = weekly()
        m.update(change)
        return youtube_lint.check(m)

    def test_rules(self):
        d = weekly()["description"]
        self.assertTrue(self.bad(description=d.replace(youtube_meta.NFA, "")))
        self.assertTrue(self.bad(description=d.replace(youtube_meta.LOGOS, "")))
        self.assertTrue(self.bad(containsSyntheticMedia=False))
        self.assertTrue(self.bad(title="Crypto Nordic #3"))
        self.assertTrue(self.bad(title="Nordic Crypto #3 #Shorts"))
        self.assertTrue(self.bad(description=d + "\nRing +47 912 34 567"))
        self.assertTrue(self.bad(description=d + "\nmail@example.com"))
        self.assertTrue(self.bad(description=d.replace("/newsletter/003/", "/nb/newsletter/003/")))
        self.assertTrue(self.bad(description=d + "\nNettside"))
        self.assertTrue(self.bad(title="Nordic Crypto: free NFT giveaway"))
        self.assertTrue(self.bad(title="Nordic Crypto: Nexa token ranking"))
        self.assertTrue(self.bad(defaultLanguage="nb"))

    def test_short_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=2", "-pix_fmt", "yuv420p",
                            os.path.join(tmp, "video.mp4")], check=True)
            self.assertEqual(youtube_lint.check(weekly(), tmp), [])
            self.assertTrue(any("1080x1920" in e for e in youtube_lint.check(story(), tmp)))


class Upload(unittest.TestCase):
    def test_resource_is_private_with_schedule(self):
        r = youtube_video_upload.resource(weekly())
        self.assertEqual(r["status"]["privacyStatus"], "private")
        self.assertEqual(r["status"]["publishAt"], "2026-10-19T07:30:00Z")
        self.assertTrue(r["status"]["containsSyntheticMedia"])
        self.assertFalse(r["status"]["selfDeclaredMadeForKids"])
        self.assertEqual(r["snippet"]["defaultLanguage"], "en")

    def test_live_issues_recorded(self):
        import json
        posted = json.load(open(youtube_video_upload.POSTED))
        self.assertEqual(posted["weekly-002"]["video_id"], "HIM3xDX5qDk")
        issues = {i["id"]: i for i in json.load(open(os.path.join(ROOT, "newsletter", "published", "issues.json")))["issues"]}
        self.assertTrue(issues["002"]["video"]["youtube"].endswith("HIM3xDX5qDk"))
        self.assertTrue(issues["001"]["video"]["youtube"].endswith("KUuaJdDTavc"))


class Captions(unittest.TestCase):
    def test_vtt_to_srt(self):
        srt = youtube_render.vtt_to_srt("WEBVTT\n\n00:01.000 --> 00:02.500\nHello\n\n00:00:03.000 --> 00:00:04.000\nWorld\n")
        self.assertEqual(srt, "1\n00:00:01,000 --> 00:00:02,500\nHello\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld\n")


if __name__ == "__main__":
    unittest.main()
