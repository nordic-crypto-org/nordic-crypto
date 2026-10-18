#!/usr/bin/env python3
"""Press release history: public list without addresses, private per-recipient log, admin page section.

  python3 -m unittest tests.test_press_history
No network: the Worker poster is a fake; logs live in a tempdir.
"""
import json, os, re, shutil, stat, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tools"))
import press_history as H
import press_release as P
from tests.test_press_release import C, ENV

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
TOKEN = "t" * 40


class History(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.tmp, True)
        self.hist = os.path.join(self.tmp, "history.json"); self.log = os.path.join(self.tmp, "state", "sends.jsonl")
        shutil.copy(H.HISTORY, self.hist); self.posts = []

    def poster(self, url, data, headers):
        self.posts.append((url, json.loads(data), headers)); return True

    def test_backfill_matches_featured_press_items_with_no_sends(self):
        feat = json.load(open(os.path.join(ROOT, "newsletter", "featured.json"), encoding="utf-8"))["items"]
        want = {i["id"]: i for i in feat if i["id"].startswith("press-")}
        rel = H.load()["releases"]
        self.assertEqual({r["id"] for r in rel}, set(want))
        for r in rel:
            self.assertEqual(r["status"], "published"); self.assertEqual(r["emails_sent"], 0)
            self.assertEqual(r["published"], want[r["id"]]["from"]); self.assertEqual(r["title"], want[r["id"]]["title"]["en"])
            self.assertEqual(r["languages"], sorted(want[r["id"]]["title"])); self.assertTrue(r["link"].startswith("https://nordiccrypto.no/"))

    def test_public_file_has_no_addresses(self):
        self.assertIsNone(EMAIL.search(open(H.HISTORY, encoding="utf-8").read()))
        h = H.load(self.hist); h["releases"][0]["note"] = "a@b.no"
        with self.assertRaises(ValueError): H.save(h, self.hist)

    def test_private_log_is_gitignored(self):
        rel = os.path.relpath(H.PRIVATE_LOG, ROOT)
        self.assertEqual(subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT).returncode, 0)

    def test_real_send_logs_privately_posts_and_counts(self):
        e = H.make_send("press-shield-regelverk", "Nordic Crypto <jqrgen@nordiccrypto.no>",
                        [("A@x.no", "sent", ""), ("b@y.se", "failed", "provider error 422")], dry_run=False)
        self.assertRegex(e["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+0[12]:00$")
        self.assertTrue(H.record_send(e, self.hist, self.log, {"NEWSLETTER_WORKER_ORIGIN": "https://w.test", "ADMIN_DELIVERY_TOKEN": TOKEN}, self.poster))
        self.assertEqual(stat.S_IMODE(os.stat(self.log).st_mode), 0o600)
        row = H.read_private(self.log)[0]
        self.assertEqual([(r["email"], r["status"]) for r in row["recipients"]], [("a@x.no", "sent"), ("b@y.se", "failed")])
        self.assertFalse(row["dry_run"]); self.assertEqual(row["from"], "Nordic Crypto <jqrgen@nordiccrypto.no>")
        url, body, hdr = self.posts[0]
        self.assertEqual(url, "https://w.test/api/admin/press-sends"); self.assertEqual(body["send"]["id"], e["id"])
        self.assertEqual(hdr["Authorization"], "Bearer " + TOKEN)
        pub = open(self.hist, encoding="utf-8").read()
        self.assertIsNone(EMAIL.search(pub)); self.assertEqual(H.load(self.hist)["releases"][0]["emails_sent"], 1)

    def test_dry_run_is_marked_and_never_counted(self):
        e = H.make_send("press-shield-regelverk", "x <jqrgen@nordiccrypto.no>", [("a@x.no", "sent", "")], dry_run=True)
        self.assertIsNone(H.record_send(e, self.hist, self.log, {}, self.poster))   # Worker not configured: local log only
        self.assertEqual(self.posts, []); self.assertTrue(e["id"].endswith("-dry"))
        self.assertEqual(H.read_private(self.log)[0]["recipients"][0]["status"], "dry_run")
        self.assertEqual(open(self.hist, encoding="utf-8").read(), open(H.HISTORY, encoding="utf-8").read())

    def test_short_token_or_http_origin_never_posts(self):
        e = H.make_send("r", "x", [], dry_run=True)
        for env in ({"NEWSLETTER_WORKER_ORIGIN": "https://w.test", "ADMIN_DELIVERY_TOKEN": "short"},
                    {"NEWSLETTER_WORKER_ORIGIN": "http://w.test", "ADMIN_DELIVERY_TOKEN": TOKEN}):
            self.assertIsNone(H.post_worker(e, env, self.poster))
        self.assertEqual(self.posts, [])


class SendScriptLogs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.tmp, True); self.logged = []

    def go(self, sender, **kw):
        rec = lambda meta, entry, env: self.logged.append((meta, entry)) or True
        return P.run("002", os.path.join(self.tmp, "out"), env=ENV, sender=sender, sleep_s=0, contacts=C, suppressed=set(),
                     ledger=os.path.join(self.tmp, "sent.json"), record=rec, **kw)

    def test_real_send_logs_each_recipient(self):
        s = self.go(lambda k, m: (m["to"] != "b@y.se", "" if m["to"] != "b@y.se" else "provider error 422"), send=True)
        meta, e = self.logged[0]
        self.assertEqual(meta["id"], "issue-002"); self.assertFalse(e["dry_run"]); self.assertEqual(s["history"], "logged")
        self.assertEqual(sorted((r["email"], r["status"]) for r in e["recipients"]), [("a@x.no", "sent"), ("b@y.se", "failed"), ("c@z.fi", "sent")])
        self.assertEqual(e["from"], "Nordic Crypto <jqrgen@nordiccrypto.no>")
        self.logged.clear(); self.go(lambda k, m: (True, ""), send=True)
        self.assertEqual([e["recipients"] for _, e in self.logged], [[{"email": "b@y.se", "status": "sent", "error": ""}]], "only the retry is logged")

    def test_explicit_dry_run_is_logged_as_dry_run_and_sends_nothing(self):
        calls = []
        self.go(lambda k, m: calls.append(m) or (True, ""), log_dry_run=True)
        self.assertEqual(calls, []); e = self.logged[0][1]
        self.assertTrue(e["dry_run"]); self.assertEqual({r["status"] for r in e["recipients"]}, {"dry_run"})

    def test_default_drafts_are_not_logged(self):
        self.go(lambda k, m: (True, "")); self.assertEqual(self.logged, [])


class AdminPage(unittest.TestCase):
    def test_press_section_lists_releases_without_addresses(self):
        import build
        html = build.admin_press_table()
        for r in H.load()["releases"]: self.assertIn(r["id"], html)
        self.assertIsNone(EMAIL.search(html))
        self.assertIn("/api/admin/press-sends", build.ADMIN_JS)


if __name__ == "__main__":
    unittest.main()
