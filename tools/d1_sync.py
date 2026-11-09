#!/usr/bin/env python3
"""Nightly fetch <-> D1.

  python3 tools/d1_sync.py restore     # fold D1 rows into the working JSON, write sources.json, restore fetch documents
  python3 tools/d1_sync.py push        # write new and pending rows and verified events; do not reopen an approved row
  python3 tools/d1_sync.py stage DEST  # copy the files the privacy gate should see

Requires NC_DATA_SOURCE=d1 and the Cloudflare token for restore and push.
stage only reads the working tree. It never copies state/private_terms.json.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools import d1_store


def _store():
    if not d1_store.enabled():
        raise d1_store.D1Error(
            "NC_DATA_SOURCE is not d1. The JSON files were not changed and D1 was not written."
        )
    return d1_store.open_remote()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else ""
    root = os.environ.get("NC_ROOT") or ROOT
    if cmd == "stage":
        if len(argv) != 2:
            print("usage: tools/d1_sync.py stage DEST", file=sys.stderr)
            return 2
        copied = d1_store.stage_for_gate(root, argv[1])
        print("d1 stage: " + (", ".join(copied) if copied else "nothing to stage"))
        return 0
    if cmd == "restore":
        try:
            result = d1_store.restore_root(_store(), root)
        except d1_store.D1Error as ex:
            # NC_D1_FALLBACK=json: leave the committed sources.json (and the other snapshots)
            # in place when D1 cannot be read. Off by default, so CI does not fetch a stale catalogue quietly.
            if os.environ.get("NC_D1_FALLBACK", "").strip().lower() != "json":
                raise
            print(
                "d1 restore: D1 unavailable (" + str(ex).splitlines()[0][:200] + "); keeping the JSON snapshot",
                file=sys.stderr,
            )
            return 0
        source_note = ""
        added = result.get("sources_added") or 0
        replaced = result.get("sources_replaced") or 0
        if added or replaced:
            source_note = f", sources {added} added and {replaced} replaced"
        print(
            "d1 restore: "
            f"{result['stories_added']} stories and {result['events_added']} events folded in"
            + source_note
            + (f", documents {', '.join(result['documents'])}" if result["documents"] else "")
        )
        return 0
    if cmd == "push":
        result = d1_store.sync_root(_store(), root, require_verified=True)
        print(f"d1 push: stories {result['stories']}, events {result['events']}, documents {result['documents']}")
        return 0
    print("usage: tools/d1_sync.py restore|push|stage DEST", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except d1_store.D1Error as ex:
        print("d1 sync: " + str(ex), file=sys.stderr)
        raise SystemExit(1)
