import datetime as dt, json, os, re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import tiktok_post as tp

UTC = dt.timezone.utc


class TikTok(unittest.TestCase):
    def test_posts(self):
        ps = tp.posts()
        self.assertEqual(len(ps), 6)
        for m in ps:
            t = dt.datetime.fromisoformat(m["when_utc"].replace("Z", "+00:00"))
            self.assertIn(t.weekday(), (0, 2, 4))
            self.assertEqual(t.hour, 17 if t.day < 25 else 18)  # 19:00 Oslo either side of 25 Oct
            if m["kind"] != "pending":
                tp.check(m)
            self.assertNotIn("shield", json.dumps(m).lower())
        by = {m["id"][:2]: m for m in ps}
        self.assertFalse(any(by[i]["aigc"] for i in ("01", "02", "06")))  # unnarrated
        self.assertTrue(all(by[i]["aigc"] for i in ("03", "04", "05")))   # AI newsreader
        self.assertNotIn("token", by["02"]["caption"].lower())

    def test_token_ranking_cut(self):
        keep = next(m for m in tp.posts() if m["id"].startswith("02"))["keep"]
        for a, b in keep:  # nothing of 22-29 s (Nexa token ranking)
            self.assertTrue(b <= 22 or a >= 29, (a, b))

    def test_cron_matches_posts(self):
        wf = (ROOT / ".github/workflows/tiktok-post.yml").read_text()
        slots = set()
        for h, days in re.findall(r'cron: "0 (\d+) ([\d,]+) 10 \*"', wf):
            slots |= {(int(d), int(h)) for d in days.split(",")}
        want = {(int(m["when_utc"][8:10]), int(m["when_utc"][11:13])) for m in tp.posts()}
        self.assertEqual(slots, want)

    def test_due(self):
        self.assertEqual(tp.due(dt.datetime(2026, 10, 21, 17, 20, tzinfo=UTC), {})["id"], "02-explorer")
        self.assertIsNone(tp.due(dt.datetime(2026, 10, 21, 17, 20, tzinfo=UTC), {"02-explorer": {}}))
        self.assertIsNone(tp.due(dt.datetime(2026, 10, 23, 17, 5, tzinfo=UTC), {}))  # pending
        self.assertIsNone(tp.due(dt.datetime(2026, 10, 21, 21, 0, tzinfo=UTC), {}))  # too late

    def test_skips_without_secrets(self):
        for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
            os.environ.pop(k, None)
        sys.argv = ["x", "--now", "2026-10-30T23:00:00Z", "--state", "/nonexistent"]
        tp.main()  # nothing due, returns quietly


if __name__ == "__main__":
    unittest.main()
