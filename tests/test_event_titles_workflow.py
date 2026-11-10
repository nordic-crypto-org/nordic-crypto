"""The event-titles workflow translates titles for every push to main that adds events (fix for 21d4ef7)."""
import os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows", "event-titles.yml")


class T(unittest.TestCase):
    def setUp(self):
        self.text = open(WF, encoding="utf-8").read()

    def test_runs_on_event_file_pushes_to_main(self):
        on = self.text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("branches: [main]", on)
        self.assertIn("- data/events.json", on)
        self.assertIn("- data/events_backfill.json", on)

    def test_translates_commits_and_checks(self):
        t = self.text
        self.assertIn("contents: write", t)
        self.assertIn("CF_AI_TOKEN: ${{ secrets.CF_AI_TOKEN }}", t)
        self.assertIn("run: python3 tools/event_translate.py", t)
        self.assertIn("git add data/event_title_i18n.json", t)
        self.assertIn("git push origin HEAD:main", t)
        self.assertIn("python3 -m unittest tests.test_event_title", t)
        self.assertLess(t.index("tools/event_translate.py"), t.index("git push origin HEAD:main"))


if __name__ == "__main__":
    unittest.main()
