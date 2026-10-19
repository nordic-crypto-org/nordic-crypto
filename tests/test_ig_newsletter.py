import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import ig_newsletter as ig


class Reel(unittest.TestCase):
    def test_cover_or_offset(self):
        m = ig.load_issue("003")
        f = ig.media_fields(m, "https://v.example/a.mp4", True)
        self.assertEqual(f["cover_url"], "https://nordiccrypto.no/newsletter/003/thumbnail-vertical.png")
        self.assertEqual(f["media_type"], "REELS"); self.assertNotIn("thumb_offset", f)
        self.assertGreater(int(ig.media_fields(m, "x", False)["thumb_offset"]), 0)
        self.assertIn(ig.issue_url(m), f["caption"]); self.assertLessEqual(len(f["caption"]), 2200)

    def test_every_issue_has_vertical_cover(self):
        for meta in json.load(open(os.path.join(ig.ROOT, "newsletter", "published", "issues.json")))["issues"]:
            self.assertTrue(os.path.exists(os.path.join(ig.ROOT, "newsletter", "published", meta["id"], "thumbnail-vertical.png")), meta["id"])

    def test_vertical_video(self):
        m = ig.load_issue("003")
        self.assertTrue(ig.video_url(m, live=lambda u: True).endswith("-vertical.mp4"))
        self.assertEqual(ig.video_url(m, live=lambda u: False), m["video"]["url"])

    def test_skips_posted_and_missing_secrets(self):
        st = os.path.join(tempfile.mkdtemp(), "ig.json")
        g, ig.graph = ig.graph, lambda *a: self.fail("must not call Graph API")
        try:
            for k in ig.ENV: os.environ.pop(k, None)
            self.assertEqual(ig.main(["--issue", "003", "--state", st]), 0)
            self.assertEqual(ig.main(["--issue", "003"]), 0)  # seeded ledger: already posted
        finally:
            ig.graph = g


if __name__ == "__main__":
    unittest.main()
