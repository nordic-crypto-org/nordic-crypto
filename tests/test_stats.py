#!/usr/bin/env python3
"""Visitor stats: weeks and months derived from daily rows, per-day paths, merging, pending state, API file
and the expandable daily-table HTML. No network and no Cloudflare token.
  python3 tests/test_stats.py
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["NC_STATS_LIVE"] = "0"
import fetch_stats as F  # noqa: E402

D = dt.date


def main():
    fails = []
    days = {D(2026, 9, 28): (3, 5), D(2026, 10, 6): (20, 21)}
    doc = F.derive(days, generated_at="2026-10-08T03:00:00Z", until=D(2026, 10, 8))
    if doc["status"] != "ok" or doc["first_date"] != "2026-09-28" or doc["last_date"] != "2026-10-08":
        fails.append(f"range {doc['first_date']}..{doc['last_date']} {doc['status']}")
    if len(doc["daily"]) != 11 or doc["daily"][-2] != {"date": "2026-10-07", "visits": 0, "pageviews": 0, "paths": []}:
        fails.append("missing days are not zero-filled")
    if not doc["daily"][-1].get("partial") or doc["daily"][-3].get("partial"):
        fails.append("only the running UTC day is partial")
    w = {r["week"]: r for r in doc["weekly"]}
    if w["2026-W40"]["visits"] != 3 or w["2026-W40"]["partial"] or w["2026-W41"]["pageviews"] != 21 or not w["2026-W41"]["partial"]:
        fails.append(f"weeks {doc['weekly']}")
    if w["2026-W41"]["start"] != "2026-10-05" or w["2026-W41"]["end"] != "2026-10-11":
        fails.append("ISO week bounds")
    m = {r["month"]: r for r in doc["monthly"]}
    if m["2026-09"]["visits"] != 3 or not m["2026-09"]["partial"] or m["2026-10"]["visits"] != 20:
        fails.append(f"months {doc['monthly']}")
    if sum(r["visits"] for r in doc["daily"]) != sum(r["visits"] for r in doc["monthly"]):
        fails.append("monthly sums differ from daily")

    allowed = {"date", "visits", "pageviews", "partial", "paths"}
    if any(set(r) - allowed for r in doc["daily"]):
        fails.append("daily rows carry more than aggregate counts and paths")
    path_allowed = {"path", "visits", "pageviews"}
    if any(set(p) - path_allowed for r in doc["daily"] for p in r.get("paths") or []):
        fails.append("path rows carry more than path, visits and pageviews")

    # 11-day span is inside the 30-day window, so every day has a paths list (empty when none were supplied).
    if any("paths" not in r for r in doc["daily"]):
        fails.append("days inside the 30-day window must have a paths list")

    pending = F.derive({}, None)
    if pending["status"] != "pending" or pending["daily"] or pending["updated_at"] is not None:
        fails.append("pending document")

    if F.clean_daily([{"date": "bad"}, {"date": "2026-10-01", "visits": "-4", "pageviews": "7"}]) != {D(2026, 10, 1): (0, 7)}:
        fails.append("clean_daily")

    if F.sanitize_path("/nb/stats/?utm=1#top") != "/nb/stats/":
        fails.append("sanitize_path must drop query strings and fragments")
    if F.sanitize_path("https://nordiccrypto.no/books/?q=1") != "/books/":
        fails.append("sanitize_path must drop host and query from a full URL")
    if F.sanitize_path("//evil.example/phish") is not None:
        fails.append("sanitize_path must reject protocol-relative URLs")
    if F.sanitize_path("") is not None or F.sanitize_path(None) is not None:
        fails.append("sanitize_path must reject empty values")
    if F.sanitize_path("stats") != "/stats":
        fails.append("sanitize_path must add a leading slash")

    merged = F.clean_paths([
        {"date": "2026-10-08", "paths": [
            {"path": "/news/?ref=twitter", "visits": 2, "pageviews": 3},
            {"path": "/news/#more", "visits": 1, "pageviews": 1},
            {"path": "https://nordiccrypto.no/stats/", "visits": 4, "pageviews": 9},
            {"path": "/news/?utm=other", "visits": "x", "pageviews": 2},
        ]},
        {"date": "bad", "paths": [{"path": "/skip", "visits": 1, "pageviews": 1}]},
    ])
    if merged != {D(2026, 10, 8): {"/news/": (3, 6), "/stats/": (4, 9)}}:
        fails.append(f"clean_paths merge {merged}")

    long_span = {D(2026, 9, 1): (1, 1), D(2026, 10, 8): (5, 6)}
    paths = {
        D(2026, 9, 1): {"/old/": (1, 1)},
        D(2026, 10, 8): {"/b/?x=1": (1, 2), "/a/": (3, 8), "/b/": (2, 2)},
    }
    wide = F.derive(long_span, generated_at="2026-10-08T03:00:00Z", until=D(2026, 10, 8), paths=paths)
    by_date = {r["date"]: r for r in wide["daily"]}
    if "paths" in by_date["2026-09-01"]:
        fails.append("paths must not be kept on days older than the last 30")
    got = by_date["2026-10-08"].get("paths")
    if got != [
        {"path": "/a/", "visits": 3, "pageviews": 8},
        {"path": "/b/", "visits": 3, "pageviews": 4},
    ]:
        fails.append(f"paths should be sanitized, merged and sorted descending {got}")

    html = F.daily_tbody(
        [{"date": "2026-10-08", "visits": 5, "pageviews": 6, "partial": True, "paths": got},
         {"date": "2026-10-07", "visits": 0, "pageviews": 0, "paths": []}],
        partial_label="partial", path_label="Path", visits_label="Visits",
        views_label="Page views", empty_label="No page breakdown for this day.",
    )
    if "<details>" not in html or "<summary>" not in html:
        fails.append("daily tbody must use details/summary")
    if html.count("<details>") != 2 or 'class="stday"' not in html:
        fails.append("each day should be an expandable stday row")
    if "/a/" not in html or "/b/" not in html or "2026-10-08" not in html:
        fails.append("expanded day must list its paths")
    if "?x=" in html or "utm=" in html or "<script" in html:
        fails.append("rendered HTML must not include query strings or raw scripts")
    if "No page breakdown for this day." not in html:
        fails.append("a day without paths should say so")
    if "partial" not in html:
        fails.append("running day should keep the partial tag")
    # A path that would break out of HTML must be escaped.
    sneaky = F.daily_tbody(
        [{"date": "2026-10-08", "visits": 1, "pageviews": 1,
          "paths": [{"path": '/"><img src=x onerror=alert(1)>', "visits": 1, "pageviews": 1}]}],
        partial_label="partial", path_label="Path", visits_label="Visits",
        views_label="Page views", empty_label="none",
    )
    if "<img" in sneaky or "&lt;img" not in sneaky:
        fails.append("path cells must be HTML-escaped")

    newer = dict(doc, generated_at="2026-10-09T03:00:00Z")
    if F.newest(doc, newer, None, F.empty()) is not newer:
        fails.append("newest picks the latest generated_at")

    old = os.environ.pop("CF_ANALYTICS_TOKEN", None)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "stats.json")
        if F.main(["--out", out]) != 0 or os.path.exists(out):
            fails.append("unconfigured run must write nothing")
        import api_feed
        # A document with paths must be written through to the public API file.
        with_paths = F.derive(
            {D(2026, 10, 8): (5, 6)}, generated_at="2026-10-08T03:00:00Z", until=D(2026, 10, 8),
            paths={D(2026, 10, 8): {"/stats/": (5, 6)}},
        )
        feed = api_feed.Feed(tmp, False, "https://nordiccrypto.no/")
        body = api_feed._stats(feed, with_paths)
        on_disk = json.load(open(os.path.join(tmp, "api", "v1", "stats.json"), encoding="utf-8"))
        if on_disk["generated_at"] != "2026-10-08T03:00:00Z" or on_disk["daily"] != with_paths["daily"] or body["status"] != "ok":
            fails.append("api/v1/stats.json")
        if on_disk["daily"][0].get("paths") != [{"path": "/stats/", "visits": 5, "pageviews": 6}]:
            fails.append("api/v1/stats.json dropped daily paths")
        if [e["id"] for e in feed.endpoints] != ["stats"]:
            fails.append("stats endpoint not registered")
    if old is not None:
        os.environ["CF_ANALYTICS_TOKEN"] = old

    if fails:
        print("FAIL:\n  " + "\n  ".join(fails))
        sys.exit(1)
    print("stats: OK")


if __name__ == "__main__":
    main()
