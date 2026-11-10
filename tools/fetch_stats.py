#!/usr/bin/env python3
"""Visitor stats for the public /stats/ page and /api/v1/stats.json.

Source: Cloudflare Web Analytics (the cookie-free JS beacon), read through the GraphQL Analytics API
(rumPageloadEventsAdaptiveGroups, filtered by the site tag). Aggregate counts per UTC day are kept:
visits and page views, and for the last 30 days visits and page views per page path. Paths have query
strings and fragments removed. No IP addresses, no user agents, no referrers, no countries.

Weeks (ISO, Monday first) and calendar months are derived from the daily rows. Days are UTC dates,
because that is how Cloudflare groups the `date` dimension.

Cloudflare keeps Web Analytics data for about six months, so each run merges the new days into the
rows already saved. The monthly table keeps growing after old days have expired at Cloudflare.
Path breakdowns are kept only for the last 30 UTC days (the window the daily table shows).

  python3 tools/fetch_stats.py                      # update data/stats.json
  python3 tools/fetch_stats.py --pages gh-pages     # also update gh-pages/api/v1/stats.json (scheduled job)
  python3 tools/fetch_stats.py --check              # print aggregate totals only, write nothing

Configuration (environment):
  CF_ANALYTICS_TOKEN   API token with Account > Account Analytics > Read (a secret; never printed)
  CF_ACCOUNT_ID        Cloudflare account id
  CF_WA_SITE_TAG       Web Analytics site tag of nordiccrypto.no (not the public beacon token)
Without all three the script prints "not configured" and exits 0 without touching any file.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "stats.json")
API_REL = os.path.join("api", "v1", "stats.json")
DATA_REL = os.path.join("data", "stats.json")   # also published at /data/stats.json
GRAPHQL = "https://api.cloudflare.com/client/v4/graphql"
SOURCE = "Cloudflare Web Analytics"
SCHEMA = 2
NOTE = ("Aggregate counts from Cloudflare Web Analytics, which uses no cookies. visits is Cloudflare's visit count "
        "(a page view that arrives from another site or with no referrer); pageviews counts every page load. "
        "For each of the last 30 UTC days, paths lists visits and page views per page path, with query strings "
        "and fragments removed. Days are UTC dates. Weeks are ISO weeks (Monday to Sunday). partial is true for "
        "a period that is not finished or that starts before the first day with data.")
DAILY_SHOWN = 30
WEEKLY_SHOWN = 26
PATH_LIMIT = 5000   # GraphQL group cap per path query; a day that hits it may omit lower-traffic paths
PATH_MAX_LEN = 200

QUERY = """query Stats($account: String!, $site: String!, $since: Date!, $until: Date!) {
  viewer { accounts(filter: {accountTag: $account}) {
    rumPageloadEventsAdaptiveGroups(limit: 1000, orderBy: [date_ASC],
      filter: {siteTag: $site, date_geq: $since, date_leq: $until}) {
      count
      sum { visits }
      dimensions { date }
    }
  } }
}"""
PATH_QUERY = """query PathStats($account: String!, $site: String!, $since: Date!, $until: Date!) {
  viewer { accounts(filter: {accountTag: $account}) {
    rumPageloadEventsAdaptiveGroups(limit: 5000, orderBy: [count_DESC],
      filter: {siteTag: $site, date_geq: $since, date_leq: $until}) {
      count
      sum { visits }
      dimensions { date requestPath }
    }
  } }
}"""
SETTINGS = """query Limits($account: String!) {
  viewer { accounts(filter: {accountTag: $account}) {
    settings { rumPageloadEventsAdaptiveGroups { notOlderThan maxDuration } }
  } }
}"""


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso_z(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty(status="pending"):
    return {"api_version": "1", "name": "Nordic Crypto", "generated_at": None, "preview": False,
            "source": SOURCE, "status": status, "timezone": "UTC", "note": NOTE, "schema": SCHEMA,
            "first_date": None, "last_date": None, "updated_at": None, "daily": [], "weekly": [], "monthly": []}


def _int(v):
    try:
        return max(0, int(v or 0))
    except (TypeError, ValueError):
        return 0


def sanitize_path(raw):
    """A site path only: no query string, fragment, host or userinfo. None when the value is not a path."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or "\x00" in s:
        return None
    if s.lower().startswith("//"):
        return None
    if "://" in s:
        u = urllib.parse.urlsplit(s)
        s = u.path or "/"
    else:
        s = s.split("?", 1)[0].split("#", 1)[0]
    s = s.strip()
    if not s:
        return "/"
    if s.startswith("//") or "\\" in s:
        return None
    if not s.startswith("/"):
        s = "/" + s
    if len(s) > PATH_MAX_LEN:
        s = s[:PATH_MAX_LEN]
    return s


def sort_paths(paths):
    """[{path, visits, pageviews}, ...] sorted by page views, then visits, then path."""
    bucket = {}
    for path, (v, p) in (paths or {}).items():
        add_path(bucket, path, v, p)
    items = [{"path": path, "visits": v, "pageviews": pv} for path, (v, pv) in bucket.items()]
    items.sort(key=lambda r: (-r["pageviews"], -r["visits"], r["path"]))
    return items


def add_path(bucket, path, visits=0, pageviews=0):
    """Merge one path's counts into {path: (visits, pageviews)}. Ignores unsanitary values."""
    clean = sanitize_path(path)
    if not clean:
        return
    ev, ep = bucket.get(clean, (0, 0))
    bucket[clean] = (ev + _int(visits), ep + _int(pageviews))


def clean_daily(rows):
    """{date: (visits, pageviews)} from any list of daily rows. Bad rows are dropped."""
    out = {}
    for r in rows or []:
        try:
            d = dt.date.fromisoformat(str(r.get("date")))
        except (TypeError, ValueError, AttributeError):
            continue
        out[d] = (_int(r.get("visits")), _int(r.get("pageviews")))
    return out


def clean_paths(rows):
    """{date: {path: (visits, pageviews)}} from daily rows, after sanitize_path. Query strings are dropped."""
    out = {}
    for r in rows or []:
        try:
            d = dt.date.fromisoformat(str(r.get("date")))
        except (TypeError, ValueError, AttributeError):
            continue
        bucket = out.setdefault(d, {})
        for item in r.get("paths") or []:
            if not isinstance(item, dict):
                continue
            add_path(bucket, item.get("path"), item.get("visits"), item.get("pageviews"))
    return out


def path_cutoff(last, today=None):
    """First UTC date that still keeps a path breakdown (last 30 days of the table, including `last`)."""
    end = last if last is not None else today
    if end is None:
        return None
    return end - dt.timedelta(days=DAILY_SHOWN - 1)


def derive(days, generated_at=None, until=None, paths=None):
    """The public document from {date: (visits, pageviews)}. Missing days between the first day with data and
    `until` (the last day the query covered) are zero. Weeks and months are sums of the daily rows.
    The day of generated_at is still running, so that day, its week and its month are marked partial.
    `paths` is {date: {path: (visits, pageviews)}}; only the last 30 UTC days keep a paths list."""
    doc = empty("ok" if days else "pending")
    doc["generated_at"] = doc["updated_at"] = generated_at
    if not days:
        return doc
    try:
        today = dt.datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).astimezone(dt.timezone.utc).date()
    except ValueError:
        today = max(days) + dt.timedelta(days=1)
    first = min(days)
    last = max([max(days)] + ([until] if until else []))
    cutoff = path_cutoff(last)
    daily, weeks, months = [], {}, {}
    d = first
    while d <= last:
        v, p = days.get(d, (0, 0))
        row = {"date": d.isoformat(), "visits": v, "pageviews": p, **({"partial": True} if d >= today else {})}
        if cutoff is not None and d >= cutoff:
            row["paths"] = sort_paths((paths or {}).get(d) or {})
        daily.append(row)
        y, w, _ = d.isocalendar()
        wk = weeks.setdefault((y, w), {"week": f"{y}-W{w:02d}", "start": (d - dt.timedelta(days=d.weekday())).isoformat(),
                                        "days": 0, "visits": 0, "pageviews": 0})
        mo = months.setdefault((d.year, d.month), {"month": f"{d.year}-{d.month:02d}", "days": 0, "visits": 0, "pageviews": 0})
        for agg in (wk, mo):
            agg["days"] += 1
            agg["visits"] += v
            agg["pageviews"] += p
        d += dt.timedelta(days=1)
    for (y, w), wk in weeks.items():
        start = dt.date.fromisoformat(wk["start"])
        wk["end"] = (start + dt.timedelta(days=6)).isoformat()
        wk["partial"] = start < first or start + dt.timedelta(days=6) >= today
    for (y, m), mo in months.items():
        start = dt.date(y, m, 1)
        nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
        mo["partial"] = start < first or nxt > today
    doc.update(first_date=first.isoformat(), last_date=last.isoformat(), daily=daily,
               weekly=[weeks[k] for k in sorted(weeks)], monthly=[months[k] for k in sorted(months)])
    return doc


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def newest(*docs):
    """The document with the latest generated_at (None when none has data)."""
    have = [d for d in docs if d and d.get("daily")]
    return max(have, key=lambda d: d.get("generated_at") or "") if have else None


_LIVE = {}


def published(base, timeout=6):
    """The copy on the live site (refreshed on gh-pages by the scheduled job). None offline or with NC_STATS_LIVE=0."""
    if os.environ.get("NC_STATS_LIVE") == "0" or not base:
        return None
    url = base.rstrip("/") + "/api/v1/stats.json"
    if url not in _LIVE:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nordic-crypto-build", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                _LIVE[url] = json.load(r)
        except Exception:
            _LIVE[url] = None
    return _LIVE[url]


def current(base=None):
    """What the build shows: the newer of data/stats.json and the published copy, re-derived from its daily rows
    so weeks and months always match the days. A pending document when neither has data."""
    doc = newest(load(DATA), published(base))
    if not doc:
        return empty()
    try:
        until = dt.date.fromisoformat(str(doc.get("last_date")))
    except ValueError:
        until = None
    return derive(clean_daily(doc.get("daily")), generated_at=doc.get("generated_at"), until=until,
                  paths=clean_paths(doc.get("daily")))


def _post(token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(GRAPHQL, data=body, method="POST",
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"stats: Cloudflare GraphQL HTTP {e.code}")
    if res.get("errors"):
        msgs = "; ".join(str(x.get("message"))[:200] for x in res["errors"])
        raise SystemExit(f"stats: Cloudflare GraphQL error: {msgs}")
    accounts = ((res.get("data") or {}).get("viewer") or {}).get("accounts") or []
    if not accounts:
        raise SystemExit("stats: the token cannot see that account")
    return accounts[0]


def fetch(token, account, site, days=400, today=None):
    """{date: (visits, pageviews)} for as many of the last `days` days as Cloudflare still keeps."""
    today = today or utc_now().date()
    lim = (_post(token, SETTINGS, {"account": account}).get("settings") or {}).get("rumPageloadEventsAdaptiveGroups") or {}
    keep_days = max(1, int(lim.get("notOlderThan") or 15552000) // 86400 - 1)
    span = max(1, int(lim.get("maxDuration") or 2678400) // 86400 - 1)
    since = max(today - dt.timedelta(days=days), today - dt.timedelta(days=keep_days))
    out = {}
    start = since
    while start <= today:
        end = min(today, start + dt.timedelta(days=span - 1))
        acc = _post(token, QUERY, {"account": account, "site": site, "since": start.isoformat(), "until": end.isoformat()})
        for r in acc.get("rumPageloadEventsAdaptiveGroups") or []:
            d = dt.date.fromisoformat(r["dimensions"]["date"])
            out[d] = (_int((r.get("sum") or {}).get("visits")), _int(r.get("count")))
        start = end + dt.timedelta(days=1)
    return out, since


def fetch_paths(token, account, site, start, end):
    """{date: {path: (visits, pageviews)}} for UTC dates start..end inclusive.

    Queries one day at a time so a busy site is less likely to hit Cloudflare's group limit silently.
    Only requestPath and date are read from the response; query strings are stripped.
    """
    out = {}
    if start is None or end is None or start > end:
        return out
    d = start
    while d <= end:
        acc = _post(token, PATH_QUERY, {"account": account, "site": site,
                                        "since": d.isoformat(), "until": d.isoformat()})
        rows = acc.get("rumPageloadEventsAdaptiveGroups") or []
        if len(rows) >= PATH_LIMIT:
            print(f"stats: path query hit the {PATH_LIMIT}-row limit on {d.isoformat()}; "
                  "lower-traffic paths for that day may be missing")
        bucket = out.setdefault(d, {})
        for r in rows:
            dim = r.get("dimensions") or {}
            add_path(bucket, dim.get("requestPath"), (r.get("sum") or {}).get("visits"), r.get("count"))
        d += dt.timedelta(days=1)
    return out


def write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, path)


def escape_html(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def ltr_html(s):
    return f'<bdi dir="ltr">{escape_html(s)}</bdi>'


def visit_cell(visits, top):
    w = round(100 * visits / max(top, 1))
    z = " z" if not w else ""
    return (f'<span class="stv"><span class="stbar" aria-hidden="true">'
            f'<span class="stfill{z}" style="width:{w}%"></span></span>'
            f'<span class="stn">{int(visits)}</span></span>')


def daily_tbody(items, *, partial_label, path_label, visits_label, views_label, empty_label):
    """HTML tbody for the per-day table: each day is a details/summary row, expandable to that day's paths."""
    items = list(items or [])
    top = max([r.get("visits") or 0 for r in items] + [1])
    out = []
    for r in items:
        date = r.get("date") or ""
        visits = _int(r.get("visits"))
        views = _int(r.get("pageviews"))
        part = f' <span class="tag">{escape_html(partial_label)}</span>' if r.get("partial") else ""
        paths = r.get("paths") or []
        if paths:
            body = "".join(
                f'<tr><th scope="row">{ltr_html(p["path"])}</th>'
                f'<td class="stn" data-label="{escape_html(visits_label)}">{_int(p.get("visits"))}</td>'
                f'<td class="stn" data-label="{escape_html(views_label)}">{_int(p.get("pageviews"))}</td></tr>'
                for p in paths
            )
            inner = (f'<table class="stpaths"><thead><tr>'
                     f'<th scope="col">{escape_html(path_label)}</th>'
                     f'<th scope="col">{escape_html(visits_label)}</th>'
                     f'<th scope="col">{escape_html(views_label)}</th>'
                     f'</tr></thead><tbody>{body}</tbody></table>')
        else:
            inner = f'<p class="stempty">{escape_html(empty_label)}</p>'
        out.append(
            f'<tr class="stday"><td colspan="3"><details>'
            f'<summary><span class="stsum">'
            f'<span class="stdate">{ltr_html(date)}{part}</span>'
            f'<span class="stvisits">{visit_cell(visits, top)}</span>'
            f'<span class="stviews stn">{views}</span>'
            f'</span></summary>{inner}</details></td></tr>'
        )
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=DATA, help="daily file to merge into (default data/stats.json)")
    ap.add_argument("--pages", help="gh-pages checkout: also merge into and write <dir>/api/v1/stats.json")
    ap.add_argument("--days", type=int, default=400)
    ap.add_argument("--check", action="store_true", help="print aggregate totals only; write nothing")
    a = ap.parse_args(argv)
    token = os.environ.get("CF_ANALYTICS_TOKEN", "").strip()
    account = os.environ.get("CF_ACCOUNT_ID", "").strip()
    site = os.environ.get("CF_WA_SITE_TAG", "").strip()
    if not (token and account and site):
        missing = [n for n, v in (("CF_ANALYTICS_TOKEN", token), ("CF_ACCOUNT_ID", account), ("CF_WA_SITE_TAG", site)) if not v]
        print(f"stats: not configured (missing {', '.join(missing)}); nothing written")
        return 0
    fresh, since = fetch(token, account, site, a.days)
    print(f"stats: {len(fresh)} days with data since {since}, visits {sum(v for v, _ in fresh.values())}, "
          f"page views {sum(p for _, p in fresh.values())}")
    now = utc_now()
    path_end = now.date()
    path_start = path_cutoff(path_end)
    fresh_paths = fetch_paths(token, account, site, path_start, path_end)
    n_paths = sum(len(p) for p in fresh_paths.values())
    print(f"stats: {n_paths} path rows over {len(fresh_paths)} days")
    if a.check:
        return 0
    targets = [a.out] + ([os.path.join(a.pages, API_REL), os.path.join(a.pages, DATA_REL)] if a.pages else [])
    days = {}
    paths = {}
    for path in targets:          # keep days Cloudflare has already expired
        old = load(path) or {}
        days.update(clean_daily(old.get("daily")))
        for d, bucket in clean_paths(old.get("daily")).items():
            paths.setdefault(d, {}).update(bucket)
    for d in [d for d in days if d >= since]:
        days.pop(d)              # the fresh query is authoritative for the window it covered
    days.update(fresh)
    for d in [d for d in paths if d >= path_start]:
        paths.pop(d)
    paths.update(fresh_paths)
    for d in [d for d in paths if d < path_start]:
        paths.pop(d)             # do not keep path lists outside the 30-day table
    if not days:                  # configured and queried, but no beacon hits yet: publish a real zero for today
        days[now.date()] = (0, 0)
    doc = derive(days, generated_at=iso_z(now), until=now.date(), paths=paths)
    for path in targets:
        write(path, doc)
        print(f"stats: wrote {os.path.relpath(path)} ({len(doc['daily'])} days, {len(doc['monthly'])} months)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
