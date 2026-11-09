#!/usr/bin/env python3
"""Sources live in D1. restore writes sources.json; add-source upserts a row. No git edit.

  python3 -m unittest tests.test_d1_sources
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools import d1_store

AT = "2026-11-09T12:00:00+00:00"
SECRET = "super-secret-token-value"

UNDOQO = {
    "id": "undoqo-plebs",
    "name": "Undoqo Plebs",
    "country": "NO",
    "url": "https://example.org/undoqo-plebs",
    "type": "manual",
    "enabled": False,
    "status": "researcher checks this by hand",
}

E24 = {
    "id": "e24",
    "name": "E24",
    "country": "NO",
    "url": "https://e24.no",
    "feed": "https://e24.no/rss2/",
    "type": "rss",
    "enabled": True,
}


def story():
    return {
        "id": "story0000001",
        "url": "https://example.org/story",
        "title": "A story",
        "status": "published",
        "summary": "Two sentences about the story. The second says what happened.",
        "approved_by": "Ed",
        "approved_at": AT,
        "country": "NO",
        "published": AT,
    }


class SourcesFromD1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nc-d1src-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.store = d1_store.open_sqlite(os.path.join(self.tmp, "c.sqlite"))
        os.makedirs(os.path.join(self.tmp, "data"))
        os.makedirs(os.path.join(self.tmp, "archive"))
        d1_store.save_json(os.path.join(self.tmp, "data", "news.json"), {"items": []})
        d1_store.save_json(os.path.join(self.tmp, "data", "events.json"), {"events": []})
        d1_store.save_json(os.path.join(self.tmp, "archive", "events.json"), {"events": []})

    def catalogue(self, sources, event_sources, **extra):
        doc = {
            "_note": "kept",
            "user_agent": "NordicCryptoBot/0.1 (+__SITE__about/; news headline bot)",
            "min_delay_seconds": 2,
            "fetch_workers": 6,
            "sources": sources,
            "event_sources": event_sources,
        }
        doc.update(extra)
        path = os.path.join(self.tmp, "sources.json")
        d1_store.save_json(path, doc)
        return path

    def test_manual_disabled_source_is_never_fetched(self):
        self.assertTrue(d1_store.researcher_only(UNDOQO))
        self.assertFalse(d1_store.news_source_fetched(dict(UNDOQO, feed="https://example.org/rss")))
        self.assertFalse(d1_store.event_source_fetched(UNDOQO))
        self.assertTrue(d1_store.news_source_fetched(E24))
        self.assertTrue(d1_store.event_source_fetched({"id": "luma-k33", "type": "luma-ical", "enabled": True}))
        # A manual source with no enabled key is on, matching events.py. The off switch is explicit.
        self.assertFalse(d1_store.researcher_only({"id": "x", "type": "manual"}))
        fetch = open(os.path.join(ROOT, "fetch.py"), encoding="utf-8").read()
        events = open(os.path.join(ROOT, "events.py"), encoding="utf-8").read()
        self.assertIn("news_source_fetched", fetch)
        self.assertIn("event_source_fetched", events)

    def test_restore_writes_d1_sources_and_leaves_a_matching_file_alone(self):
        path = self.catalogue([E24], [])
        before = open(path, encoding="utf-8").read()
        d1_store.import_sources(self.store, [E24], "news", AT)
        same = d1_store.restore_root(self.store, self.tmp)
        self.assertEqual((same["sources_added"], same["sources_replaced"]), (0, 0))
        self.assertEqual(open(path, encoding="utf-8").read(), before)

        plan = d1_store.plan_source_upsert(None, UNDOQO, "event", "Ed", AT, note="Checked by hand.")
        d1_store.apply_source_upsert(self.store, plan, "Ed", AT)
        # A rejected news row must not come back switched on.
        d1_store.import_sources(self.store, [dict(E24, id="old-feed", name="Old")], "news", AT)
        self.store.execute(
            "UPDATE sources SET review_status = 'rejected', enabled = 1 WHERE id = 'old-feed'"
        )
        folded = d1_store.restore_root(self.store, self.tmp)
        self.assertGreaterEqual(folded["sources_added"], 1)
        doc = json.load(open(path, encoding="utf-8"))
        self.assertEqual(doc["user_agent"], "NordicCryptoBot/0.1 (+__SITE__about/; news headline bot)")
        self.assertEqual(doc["min_delay_seconds"], 2)
        self.assertEqual(doc["fetch_workers"], 6)
        by_id = {row["id"]: row for row in doc["event_sources"]}
        self.assertEqual(by_id["undoqo-plebs"]["type"], "manual")
        self.assertIs(by_id["undoqo-plebs"]["enabled"], False)
        self.assertNotIn("Checked by hand.", json.dumps(doc))
        news = {row["id"]: row for row in doc["sources"]}
        self.assertIs(news["e24"]["enabled"], True)
        self.assertIs(news["old-feed"]["enabled"], False)
        self.assertFalse(d1_store.event_source_fetched(by_id["undoqo-plebs"]))
        self.assertFalse(d1_store.news_source_fetched(news["old-feed"]))

    def test_restore_replaces_a_stale_git_copy_and_an_empty_table_does_not_blank_the_file(self):
        path = self.catalogue([E24], [{"id": "meetup", "name": "Meetup", "type": "jsonld", "enabled": True, "url": "https://example.org/m"}])
        edited = dict(E24, feed="https://e24.no/new.xml")
        d1_store.import_sources(self.store, [edited], "news", AT)
        d1_store.import_sources(self.store, [{"id": "meetup", "name": "Meetup", "type": "jsonld", "enabled": False, "url": "https://example.org/m"}], "event", AT)
        result = d1_store.restore_root(self.store, self.tmp)
        self.assertEqual(result["sources_added"], 0)
        self.assertGreaterEqual(result["sources_replaced"], 1)
        doc = json.load(open(path, encoding="utf-8"))
        self.assertEqual(doc["sources"][0]["feed"], "https://e24.no/new.xml")
        self.assertIs(doc["event_sources"][0]["enabled"], False)
        self.assertEqual(doc["_note"], "kept")

        empty = d1_store.open_sqlite(os.path.join(self.tmp, "empty.sqlite"))
        again = open(path, encoding="utf-8").read()
        stats = d1_store.write_sources_from_store(empty, self.tmp)
        self.assertEqual(stats, {"sources_added": 0, "sources_replaced": 0})
        self.assertEqual(open(path, encoding="utf-8").read(), again)

    def test_materialize_writes_sources_for_the_build(self):
        d1_store.sync_story(self.store, story(), AT)
        d1_store.apply_source_upsert(
            self.store, d1_store.plan_source_upsert(None, UNDOQO, "event", "Ed", AT), "Ed", AT,
        )
        self.catalogue([E24], [])
        d1_store.materialize(self.tmp, store=self.store, at=AT)
        doc = json.load(open(os.path.join(self.tmp, "sources.json"), encoding="utf-8"))
        ids = [row["id"] for row in doc["event_sources"]]
        self.assertEqual(ids, ["undoqo-plebs"])
        self.assertIs(doc["event_sources"][0]["enabled"], False)
        self.assertEqual(doc["sources"][0]["id"], "e24")

    def test_add_source_upserts_and_import_does_not_overwrite_it(self):
        plan = d1_store.plan_source_upsert(None, UNDOQO, "event", "Ed", AT, note="Checked by hand.")
        self.assertEqual(plan["enabled"], 0)
        self.assertNotIn("Checked by hand.", plan["payload"])
        d1_store.apply_source_upsert(self.store, plan, "Ed", AT)
        row = d1_store.one(self.store, "SELECT * FROM sources WHERE id = 'undoqo-plebs'")
        changed = d1_store.plan_source_upsert(
            row, dict(UNDOQO, name="Undoqo Plebs (hand)"), "event", "Ed", AT, enabled=False,
        )
        d1_store.apply_source_upsert(self.store, changed, "Ed", AT)
        row = d1_store.one(self.store, "SELECT * FROM sources WHERE id = 'undoqo-plebs'")
        self.assertEqual(json.loads(row["payload"])["name"], "Undoqo Plebs (hand)")
        self.assertEqual(row["review_note"], "Checked by hand.")
        self.assertEqual(row["enabled"], 0)
        # The git snapshot still has the old name. Import must not put it back.
        d1_store.import_root(self.store, self._root_with_old_name(), AT)
        row = d1_store.one(self.store, "SELECT payload, enabled FROM sources WHERE id = 'undoqo-plebs'")
        self.assertEqual(json.loads(row["payload"])["name"], "Undoqo Plebs (hand)")
        self.assertEqual(row["enabled"], 0)
        sql = d1_store.source_upsert_sql(
            d1_store.plan_source_upsert(None, dict(UNDOQO, id="other-manual"), "news", "Ed", AT, enabled=False, note="n"),
            "Ed",
        )
        self.assertTrue(sql.startswith("INSERT INTO sources"))
        self.assertIn("other-manual", sql)
        self.store.executescript(sql)

    def _root_with_old_name(self):
        root = os.path.join(self.tmp, "git")
        os.makedirs(os.path.join(root, "data"))
        os.makedirs(os.path.join(root, "archive"))
        d1_store.save_json(os.path.join(root, "data", "news.json"), {"items": []})
        d1_store.save_json(os.path.join(root, "data", "events.json"), {"events": []})
        d1_store.save_json(os.path.join(root, "archive", "events.json"), {"events": []})
        d1_store.save_json(os.path.join(root, "sources.json"), {"sources": [], "event_sources": [UNDOQO]})
        return root

    def test_add_source_cli_and_restore_fallback(self):
        path = os.path.join(self.tmp, "cli.sqlite")
        payload = os.path.join(self.tmp, "source.json")
        d1_store.save_json(payload, UNDOQO)
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "d1_review.py"),
             "--sqlite", path, "add-source", "--kind", "event", "--json", payload,
             "--enabled", "false", "--note", "Checked by hand.", "--by", "Ed"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("undoqo-plebs", proc.stdout)
        self.assertNotIn(SECRET, proc.stdout + proc.stderr)
        store = d1_store.open_sqlite(path)
        row = d1_store.one(store, "SELECT kind, enabled, review_note, payload FROM sources WHERE id = 'undoqo-plebs'")
        self.assertEqual((row["kind"], row["enabled"], row["review_note"]), ("event", 0, "Checked by hand."))
        self.assertEqual(json.loads(row["payload"])["type"], "manual")
        again = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "d1_review.py"),
             "--sqlite", path, "add-source", "--kind", "event", "--json", payload,
             "--set", "name=Undoqo Plebs updated", "--by", "Ed"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("updated", again.stdout)
        store = d1_store.open_sqlite(path)
        row = d1_store.one(store, "SELECT review_note, payload FROM sources WHERE id = 'undoqo-plebs'")
        self.assertEqual(json.loads(row["payload"])["name"], "Undoqo Plebs updated")
        self.assertEqual(row["review_note"], "Checked by hand.")

        catalogue = self.catalogue([E24], [])
        before = open(catalogue, encoding="utf-8").read()
        env = os.environ.copy()
        env["NC_DATA_SOURCE"] = "d1"
        env["NC_D1_FALLBACK"] = "json"
        env["NC_ROOT"] = self.tmp
        env["CLOUDFLARE_API_TOKEN"] = SECRET
        env.pop("CF_ACCOUNT_ID", None)
        env.pop("CLOUDFLARE_ACCOUNT_ID", None)
        env.pop("CF_D1_DATABASE_ID", None)
        kept = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "d1_sync.py"), "restore"],
            cwd=ROOT, env=env, check=False, capture_output=True, text=True,
        )
        self.assertEqual(kept.returncode, 0, kept.stderr)
        self.assertIn("JSON snapshot", kept.stderr)
        self.assertNotIn(SECRET, kept.stdout + kept.stderr)
        self.assertEqual(open(catalogue, encoding="utf-8").read(), before)

        env.pop("NC_D1_FALLBACK")
        failed = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "d1_sync.py"), "restore"],
            cwd=ROOT, env=env, check=False, capture_output=True, text=True,
        )
        self.assertEqual(failed.returncode, 1)
        self.assertNotIn(SECRET, failed.stdout + failed.stderr)
        self.assertEqual(open(catalogue, encoding="utf-8").read(), before)


if __name__ == "__main__":
    unittest.main()
