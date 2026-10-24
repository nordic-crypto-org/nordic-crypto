#!/usr/bin/env python3
"""Sync campaigns and scheduled posts to the admin-only D1 tables (tipworker migrations/0010, GET /api/admin/schedule).

The data is private: it lives in a JSON file outside the repo (default state/admin/schedule.json, gitignored) and in D1,
never in the repo or on the site. Times of GitHub Actions jobs are read from .github/workflows/*.yml, not copied.

  {"campaigns": [{id, name, channels, what, starts_at, ends_at, status}],
   "schedule":  [{id, channel, what, cron | at, tz?, status, source?, campaign_id?}],     # routines outside the repo
   "workflows": {"x-newsletter.yml": {"channel": "X", "what": "...", "status": "active"}}}
status: active | paused | awaiting_approval | awaiting_setup | done. cron is in tz (default Europe/Oslo); at is Oslo time.

  python3 tools/admin_schedule.py [--config PATH] [--check]   --check: validate and count, post nothing
Needs NEWSLETTER_WORKER_ORIGIN and ADMIN_DELIVERY_TOKEN (never printed).
"""
import json, os, re, sys, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "state", "admin", "schedule.json")
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")
CRON = re.compile(r"""^\s*-\s*cron:\s*["']([^"']+)["']""", re.M)


def workflow_crons(name, root=WORKFLOWS):
    with open(os.path.join(root, os.path.basename(name)), encoding="utf-8") as f: return CRON.findall(f.read())


def payload(cfg, root=WORKFLOWS):
    rows = list(cfg.get("schedule") or [])
    for wf, meta in (cfg.get("workflows") or {}).items():
        for i, cron in enumerate(workflow_crons(wf, root)):
            rows.append({**meta, "id": f"wf:{wf}:{i}", "cron": cron, "tz": "UTC", "source": "workflow:" + wf})
    return {"campaigns": list(cfg.get("campaigns") or []), "schedule": rows}


def post(data, env=None):
    env = os.environ if env is None else env
    origin, tok = (env.get("NEWSLETTER_WORKER_ORIGIN") or "").rstrip("/"), env.get("ADMIN_DELIVERY_TOKEN") or ""
    if not origin.startswith("https://") or len(tok) < 32: return None
    req = urllib.request.Request(origin + "/api/admin/schedule", data=json.dumps(data).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json",
                                          "User-Agent": "nordic-crypto-admin-schedule/1"})   # Cloudflare 1010 blocks Python-urllib
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return 200 <= r.status < 300
    except (urllib.error.URLError, OSError): return False


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if "-h" in a or "--help" in a: print(__doc__.strip()); return 0
    path = a[a.index("--config") + 1] if "--config" in a else CONFIG
    data = payload(json.load(open(path, encoding="utf-8")))
    n = f"{len(data['campaigns'])} campaigns, {len(data['schedule'])} schedule rows"
    if "--check" in a: print("admin schedule:", n); return 0
    r = post(data)
    if r is None: print("admin schedule: NEWSLETTER_WORKER_ORIGIN / ADMIN_DELIVERY_TOKEN not set"); return 1
    print("admin schedule:", n, "synced" if r else "FAILED"); return 0 if r else 1


if __name__ == "__main__":
    sys.exit(main())
