#!/usr/bin/env python3
"""Academia rows in the existing D1 database.

  python3 -m unittest tests.test_d1_academia
"""
import json
import os
import shutil
import sqlite3
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)
from tools import d1_academia
from tools import d1_review
from tools import d1_store

AT = "2026-11-09T12:00:00+00:00"


class AcademiaD1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nc-d1ac-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.store = d1_store.open_sqlite(os.path.join(self.tmp, "content.sqlite"))

    def test_checkout_import_is_idempotent_and_keeps_the_named_rows_singular(self):
        first = d1_academia.import_checkout(self.store, ROOT, AT)
        counts = first["counts"]
        self.assertEqual(counts["total"], 844)
        self.assertEqual(counts["approved"], 452)
        self.assertEqual(counts["sections"]["courses"], {"total": 15, "approved": 9})
        self.assertEqual(counts["sections"]["groups"], {"total": 11, "approved": 4})
        self.assertEqual(counts["sections"]["publications"], {"total": 779, "approved": 408})
        self.assertEqual(counts["sections"]["research"], {"total": 39, "approved": 31})
        self.assertEqual(first["inserted"], 844)
        self.assertEqual(first["guarded"], 0)
        batches = {row["file"]: row for row in first["batches"]}
        self.assertEqual(batches["2026-11-09-copenhagen.json"]["inserted"], 12)
        self.assertEqual(batches["2026-11-09-helsinki.json"]["inserted"], 15)

        second = d1_academia.import_checkout(self.store, ROOT, AT)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["updated"], 0)
        self.assertEqual(second["counts"]["total"], 844)

        def names(section):
            return [row["name"] for row in self.store.query(
                "SELECT name FROM academia WHERE section = ? ORDER BY name", (section,),
            )]

        research = names("research")
        groups = names("groups")
        self.assertEqual(research.count("European Blockchain Center (EBC)"), 1)
        self.assertEqual(research.count("Helsinki Blockchain Center (HBC)"), 1)
        self.assertEqual(sum(1 for name in research if "COBRA" in name), 1)
        self.assertEqual(groups.count("CBS Bitcoin"), 1)
        self.assertEqual(groups.count("CBS Fintech"), 1)
        self.assertEqual(groups.count("CBS Blockchain Society"), 1)
        self.assertEqual(groups.count("Aalto Bitcoin"), 1)
        self.assertEqual(groups.count("Aalto Crypto Society"), 1)
        self.assertEqual(sum(1 for name in groups if "Blockchain Student Group" in name), 1)

        copenhagen_groups = self.store.query(
            "SELECT name, status, active FROM academia WHERE section = 'groups' AND name IN ('CBS Fintech', 'CBS Blockchain Society') ORDER BY name",
            (),
        )
        self.assertEqual(
            [(row["name"], row["status"], row["active"]) for row in copenhagen_groups],
            [("CBS Blockchain Society", "pending", 0), ("CBS Fintech", "pending", 0)],
        )
        helsinki_groups = {
            row["name"]: row for row in self.store.query(
                "SELECT name, status, active FROM academia WHERE section = 'groups' AND country = 'FI'",
                (),
            )
        }
        self.assertEqual(helsinki_groups["Aalto Bitcoin"]["status"], "approved")
        self.assertEqual(helsinki_groups["Aalto Crypto Society"]["status"], "pending")
        self.assertEqual(helsinki_groups["Aalto Crypto Society"]["active"], 0)
        self.assertEqual(helsinki_groups["Blockchain Forum Finland"]["status"], "pending")
        self.assertEqual(helsinki_groups["Blockchain Forum Finland"]["active"], 1)
        self.assertEqual(helsinki_groups["Suomen Kryptovaluuttayhdistys Konsensus ry"]["active"], 1)

        for code in ("CS-AJ0100", "COMM.NET.500", "LT00DF90", "ECON-CV002", "ICT4HM103"):
            rows = self.store.query("SELECT status FROM academia WHERE section = 'courses' AND code = ?", (code,))
            self.assertEqual(len(rows), 1, code)
        self.assertEqual(
            self.store.query("SELECT status FROM academia WHERE code = 'ECON-CV002'")[0]["status"],
            "approved",
        )
        ebc = json.loads(d1_store.one(
            self.store, "SELECT payload FROM academia WHERE name = ?",
            ("European Blockchain Center (EBC)",),
        )["payload"])
        self.assertEqual(ebc["status"], "approved")
        self.assertNotIn("@", ebc["editor_note"])

        doc = d1_academia.document(self.store)
        public = d1_academia.public_sections(doc)
        self.assertEqual(sum(len(rows) for rows in public.values()), 452)
        self.assertTrue(all(row["status"] == "approved" for rows in public.values() for row in rows))
        self.assertFalse(any(row["name"] == "CBS Fintech" for row in public["groups"]))
        self.assertTrue(any(row["name"] == "European Blockchain Center (EBC)" for row in public["research"]))
        self.assertTrue(any(row["code"] == "ICT4HM103" for row in public["courses"]))

        guarded = d1_academia.upsert_document(self.store, {
            "research": [{
                "country": "DK",
                "name": "COBRA Aarhus",
                "institution": "Aarhus University",
                "about": "A shorter name for the centre already listed.",
                "url": "https://example.org/cobra-again",
                "source": "https://example.org/cobra-again",
                "checked": "2026-11-09",
                "status": "approved",
                "editor_note": "must not be inserted",
            }],
            "courses": [{
                "country": "FI",
                "institution": "Aalto University",
                "code": "CS-AJ0100",
                "name": "Blockchain Business Applications",
                "level": "Basic",
                "term": "Past",
                "about": "Already listed.",
                "url": "https://example.org/cs-aj0100",
                "source": "https://example.org/cs-aj0100",
                "checked": "2026-11-09",
                "status": "approved",
                "editor_note": "must not be inserted",
            }],
        }, AT, update=False)
        self.assertEqual(guarded["inserted"], 0)
        self.assertGreaterEqual(guarded["guarded"] + guarded["kept"] + guarded["unchanged"], 2)
        self.assertEqual(d1_academia.counts(self.store)["total"], 844)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.execute("DELETE FROM academia WHERE section = 'courses'")

    def test_add_academia_command_upserts_without_a_code_change(self):
        path = os.path.join(self.tmp, "batch.json")
        d1_store.save_json(path, {"research": [{
            "country": "FI", "name": "Example Helsinki Lab", "institution": "University of Helsinki",
            "about": "A later batch.", "url": "https://example.org/lab", "source": "https://example.org/lab",
            "checked": "2026-11-09", "status": "approved", "editor_note": "added by the data command",
        }]})
        code = d1_review.main(["add-academia", "--json", path, "--sqlite", self.store.path])
        self.assertEqual(code, 0)
        row = d1_store.one(self.store, "SELECT status FROM academia WHERE name = 'Example Helsinki Lab'")
        self.assertEqual(row["status"], "approved")
        again = d1_review.main(["add-academia", "--json", path, "--sqlite", self.store.path, "--keep"])
        self.assertEqual(again, 0)
        self.assertEqual(d1_academia.counts(self.store)["total"], 1)

    def test_backup_redacts_addresses_and_the_page_falls_back(self):
        d1_academia.import_checkout(self.store, ROOT, AT)
        dest = os.path.join(self.tmp, "backup")
        d1_store.write_backup(self.store, dest)
        blob = open(os.path.join(dest, "academia.json"), encoding="utf-8").read()
        self.assertNotIn("info@kthbci.org", blob)
        self.assertIn("European Blockchain Center (EBC)", blob)
        build = open(os.path.join(ROOT, "build.py"), encoding="utf-8").read()
        self.assertIn("using data/academia.json", build)
        self.assertIn("D1 has no rows", build)
        worker = open(os.path.join(ROOT, "workers", "content", "src", "worker.js"), encoding="utf-8").read()
        self.assertIn("/api/v1/academia.json", worker)
        self.assertIn("status !== \"approved\"", worker)


if __name__ == "__main__":
    unittest.main()
