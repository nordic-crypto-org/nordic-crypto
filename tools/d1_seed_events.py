#!/usr/bin/env python3
"""Upsert the verified calendar rows into D1.

Reads those rows from data/events.json (the offline snapshot). Matches an
existing D1 row on id, then on title+date+city. Impact Onchain moved from
4 November 2026 to 11 November: the 4 November row is updated in place.
A second run writes nothing.

  python3 tools/d1_seed_events.py --sqlite FILE
  python3 tools/d1_seed_events.py                 # remote; needs the token and ids

Does not print the Cloudflare token. Does not create the database.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools import d1_store

# Stable ids. Impact Onchain keeps the id it already had on 4 November.
SEED_IDS = ("fb0847fb538e", "43e778cb5318", "6054d96c8b8f")
MOVED = ("impact onchain", "2026-11-04")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Upsert verified events into D1")
    parser.add_argument("--sqlite", help="write a local SQLite file instead of D1")
    parser.add_argument("--root", default=ROOT)
    args = parser.parse_args(argv)
    if args.sqlite:
        store = d1_store.open_sqlite(args.sqlite)
    else:
        missing = d1_store.missing_remote()
        if missing:
            print(d1_store.SETUP_COMMANDS, file=sys.stderr)
            print("missing " + ", ".join(missing), file=sys.stderr)
            return 2
        store = d1_store.open_remote()
    stats = d1_store.seed_events(store, args.root, SEED_IDS, MOVED)
    print(
        "d1 seed: "
        f"inserted {stats['inserted']}, updated {stats['updated']}, skipped {stats['skipped']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except d1_store.D1Error as ex:
        print("d1 seed: " + str(ex), file=sys.stderr)
        raise SystemExit(1)
