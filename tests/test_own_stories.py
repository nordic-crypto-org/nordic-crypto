import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build, i18n

class OwnStories(unittest.TestCase):
    def test_committed_story_without_queue(self):
        real = build.load
        build.load = lambda p, d=None: d if p.endswith(os.path.join("queue", "approved.json")) else real(p, d)
        try:
            build.LANG = "en"; items = {i["id"]: i for i in build.build_stories(write=False)}
        finally:
            build.load = real
        it = items["story-tiny-viking-marfa"]
        self.assertEqual(it["status"], "published")
        self.assertEqual(it["published"], "2026-10-20T22:32:00+02:00")
        for l in i18n.ALL_LANGS[1:]:
            self.assertTrue(it["summary_i18n"][l].strip() and it["title_i18n"][l].strip(), l)
        for l in ("hi", "bn", "ur"):
            self.assertIn("Tiny Vikings", it["summary_i18n"][l])

if __name__ == "__main__":
    unittest.main()
