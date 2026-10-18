#!/usr/bin/env python3
"""Every public data file and /api/v1/ collection is documented on /db/ (schema/*.schema.json).
  python3 -m unittest tests.test_db_coverage
"""
import glob
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import schema_db

# Internal state, raw inputs and fixtures; not public collections.
INTERNAL_FILES = {
    "academia_i18n.json", "event_nft_fixture.json", "events_backfill_state.json", "fb_posted.json", "no_en.json",
    "orgchart_no_raw.json", "orgchart_nordic.json", "orgchart_speakers.json", "talks-backfill-state.json", "x_posted.json",
}
# Discovery/meta endpoints, archive pagination and the flag-gated treasury prototype.
NON_COLLECTION_API = (
    r"/api/v1/(index|meta|openapi|languages|geo-language)\.json", r"/api/v1/schema/index\.json",
    r"/api/v1/archive/news/page-[^/]+\.json", r"/api/v1/archive/articles/[^/]+\.json",
    r"/api/v1/orgchart/relations/[^/]+\.json", r"/api/v1/treasury(/history)?\.json",
)


def documented():
    files, apis = set(), []
    for _, schema in schema_db.load_schemas():
        meta = schema.get("x-nordic") or {}
        files |= set(meta.get("files") or [])
        apis += [re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(a["path"])) for a in meta.get("api") or []]
    return files, apis


class DbCoverage(unittest.TestCase):
    def test_data_files(self):
        files, _ = documented()
        missing = [p for p in sorted(glob.glob(os.path.join(ROOT, "data", "*.json")))
                   if os.path.relpath(p, ROOT) not in files and os.path.basename(p) not in INTERNAL_FILES]
        self.assertEqual(missing, [], "add a schema/*.schema.json (shown on /db/) or list as internal")

    def test_api_collections(self):
        _, apis = documented()
        src = open(os.path.join(ROOT, "tools", "api_feed.py"), encoding="utf-8").read()
        used = sorted({"/" + p for p in re.findall(r"api/v1/[\w/{}.-]+\.json", src)})
        missing = [p for p in used if not any(re.fullmatch(a, p) for a in apis)
                   and not any(re.fullmatch(r, p) for r in NON_COLLECTION_API)]
        self.assertEqual(missing, [], "add the endpoint to a schema's x-nordic.api so /db/ lists it")


if __name__ == "__main__":
    unittest.main()
