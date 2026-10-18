#!/usr/bin/env python3
"""Press release history: which releases exist and, privately, who each send went to.

Public (committed, shown on /admin/): data/press/history.json. One entry per release with id, title, languages,
publish date, link, status and the number of addresses emailed so far. Never any address.

Private (recipients are personal data, never committed or published):
  state/press/sends.jsonl   local append-only log (gitignored, mode 0600), one line per send
  Worker D1 press_sends     POST /api/admin/press-sends with ADMIN_DELIVERY_TOKEN; read back only by a signed-in
                            admin via GET /api/admin/press-sends (tipworker/src/admin.js, migrations/0008).

  python3 tools/press_history.py --sync   re-post every logged send to the Worker (idempotent by send id)
"""
import datetime, json, os, re, sys, urllib.error, urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(ROOT, "data", "press", "history.json")
PRIVATE_LOG = os.path.join(ROOT, "state", "press", "sends.jsonl")
OSLO = ZoneInfo("Europe/Oslo")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
STATUSES = {"sent", "failed", "dry_run"}


def oslo_now():
    return datetime.datetime.now(OSLO).replace(microsecond=0).isoformat()


def load(path=HISTORY):
    try: return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError: return {"releases": []}


def save(hist, path=HISTORY):
    for r in hist.get("releases", []):
        if any(EMAIL.search(str(v)) for v in r.values()): raise ValueError("press history: no addresses in the public file")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(hist, f, ensure_ascii=False, indent=1); f.write("\n")
    os.replace(tmp, path)


def ensure_release(hist, rid, title, languages, published, link, status="published"):
    """Adds the release if it is not listed yet; returns its entry."""
    for r in hist.setdefault("releases", []):
        if r["id"] == rid: return r
    r = {"id": rid, "title": title, "languages": sorted(languages), "published": published, "link": link,
         "status": status, "emails_sent": 0}
    hist["releases"].append(r)
    return r


def make_send(release_id, from_addr, results, dry_run, at=None):
    """results: [(email, status, error)], status sent/failed (dry_run for a dry run)."""
    at = at or oslo_now()
    rec = [{"email": e.strip().lower(), "status": "dry_run" if dry_run else s, "error": (err or "")[:80]} for e, s, err in results]
    for r in rec:
        if r["status"] not in STATUSES: raise ValueError("press history: bad status")
    return {"id": f"{release_id}-{re.sub(r'[^0-9]', '', at)[:14]}{'-dry' if dry_run else ''}", "release_id": release_id, "at": at,
            "from": from_addr, "dry_run": bool(dry_run), "recipients": rec,
            "sent": sum(r["status"] == "sent" for r in rec), "failed": sum(r["status"] == "failed" for r in rec)}


def append_private(entry, path=PRIVATE_LOG):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f: f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)


def read_private(path=PRIVATE_LOG):
    if not os.path.exists(path): return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def http_post(url, data, headers, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return 200 <= r.status < 300
    except (urllib.error.URLError, OSError): return False


def post_worker(entry, env=None, poster=http_post):
    """True if the Worker stored it, None if not configured, False on error. Never logs the token."""
    env = os.environ if env is None else env
    origin, tok = (env.get("NEWSLETTER_WORKER_ORIGIN") or "").rstrip("/"), env.get("ADMIN_DELIVERY_TOKEN") or ""
    if not origin.startswith("https://") or len(tok) < 32: return None
    return poster(origin + "/api/admin/press-sends", json.dumps({"send": entry}).encode(),
                  {"Authorization": "Bearer " + tok, "Content-Type": "application/json"})


def record_send(entry, history=HISTORY, log=PRIVATE_LOG, env=None, poster=http_post):
    """Private log first (always), then the Worker, then the public count (real sends only)."""
    append_private(entry, log)
    stored = post_worker(entry, env, poster)
    if not entry["dry_run"] and entry["sent"]:
        hist = load(history)
        for r in hist.get("releases", []):
            if r["id"] == entry["release_id"]: r["emails_sent"] = r.get("emails_sent", 0) + entry["sent"]
        save(hist, history)
    return stored


def log_run(release, entry, history=HISTORY, log=PRIVATE_LOG, env=None, poster=http_post):
    """release: dict(id, title, languages, published, link). A real send lists the release publicly if needed."""
    if not entry["dry_run"]:
        hist = load(history)
        ensure_release(hist, release["id"], release["title"], release["languages"], release["published"], release["link"])
        save(hist, history)
    return record_send(entry, history, log, env, poster)


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if a != ["--sync"]: print(__doc__.strip()); return 2
    ok = bad = 0
    for e in read_private():
        r = post_worker(e)
        if r is None: print("press history: NEWSLETTER_WORKER_ORIGIN / ADMIN_DELIVERY_TOKEN not set"); return 1
        ok += bool(r); bad += not r
    print(f"press history: {ok} synced, {bad} failed"); return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
