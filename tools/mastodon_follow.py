#!/usr/bin/env python3
"""Follow accounts that post under crypto hashtags (#bitcoin, #crypto, #nostr…) as @nordiccrypto on Mastodon.

Stays inside Mastodon's 400 follows/day cap: follows at most --max per run, stops on HTTP 429
or when X-RateLimit-Remaining drops to --reserve, and never re-follows an id in the ledger.
Env: MASTODON_TOKEN (scopes: read, write:follows), MASTODON_BASE (default https://mastodon.social).
"""
import argparse, datetime as dt, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from itertools import zip_longest

BASE = os.environ.get("MASTODON_BASE", "https://mastodon.social").rstrip("/")
UA = "nordic-crypto-mastodon-follow/1.0"
MIN_FOLLOWERS, MIN_STATUSES, MIN_AGE_DAYS, PER_DOMAIN = 10, 10, 14, 2
SKIP_DOMAINS = ("brid.gy", "lemmy", "kbin", "mbin", "pixelfed")  # bridges and non-microblog servers
TAGS = ("bitcoin", "crypto", "cryptocurrency", "nostr", "btc", "lightning", "ethereum", "blockchain", "bitcoincash", "defi")


def log(msg):
    print(msg, file=sys.stderr, flush=True)


class RateLimited(Exception):
    pass


class Client:
    def __init__(self, token, base=BASE):
        self.token, self.base = token, base

    def call(self, method, path, params=None):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        req = urllib.request.Request(url, method=method, data=b"" if method == "POST" else None,
                                     headers={"Authorization": f"Bearer {self.token}", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimited(e.headers.get("X-RateLimit-Reset", "")) from None
            raise


def candidates(timelines):
    """Authors of recent posts per hashtag, round-robin across tags so no tag dominates; unique ids."""
    seen, out = set(), []
    for row in zip_longest(*timelines):
        for st in row:
            acct = (st or {}).get("account") or {}
            aid = acct.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                out.append(acct)
    return out


def domain(acct):
    return acct.get("acct", "").partition("@")[2].lower()


def looks_real(acct, now=None):
    """Drop fresh, empty or bridged accounts: spam floods tag timelines with them."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if any(d in domain(acct) for d in SKIP_DOMAINS):
        return False
    if (acct.get("followers_count") or 0) < MIN_FOLLOWERS or (acct.get("statuses_count") or 0) < MIN_STATUSES:
        return False
    try:
        created = dt.datetime.fromisoformat(acct["created_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError):
        return False
    return now - created >= dt.timedelta(days=MIN_AGE_DAYS)


def eligible(acct, me_id, ledger, rel):
    """Skip ourselves, bots, groups, locked/moved/suspended accounts, past follows and current follows."""
    if acct["id"] == me_id or acct["id"] in ledger:
        return False
    if acct.get("bot") or acct.get("group") or acct.get("locked") or acct.get("moved") or acct.get("suspended"):
        return False
    r = rel.get(acct["id"], {})
    return not (r.get("following") or r.get("requested") or r.get("blocking") or r.get("blocked_by")
                or r.get("muting") or r.get("domain_blocking"))


def pick(pool, me_id, ledger, rel, max_follows):
    """Eligible, real-looking accounts, at most PER_DOMAIN from any one remote server per run."""
    out, per = [], {}
    for a in pool:
        if not (eligible(a, me_id, ledger, rel) and looks_real(a)):
            continue
        d = domain(a)
        if d and per.get(d, 0) >= PER_DOMAIN:
            continue
        per[d] = per.get(d, 0) + 1
        out.append(a)
        if len(out) >= max_follows:
            break
    return out


def load_ledger(path):
    try:
        with open(path) as f:
            return set(json.load(f))
    except (FileNotFoundError, ValueError):
        return set()


def save_ledger(path, ledger):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(ledger), f)


def run(client, ledger, max_follows, reserve, dry_run=False, pause=3.0, sleep=time.sleep, tags=TAGS):
    me, _ = client.call("GET", "/api/v1/accounts/verify_credentials")
    timelines = []
    for tag in tags:
        try:
            rows, _ = client.call("GET", f"/api/v1/timelines/tag/{urllib.parse.quote(tag)}", {"limit": 40})
            timelines.append(rows)
        except urllib.error.HTTPError as e:
            log(f"#{tag}: HTTP {e.code}; skipping")
    pool = candidates(timelines)
    rel = {}
    for i in range(0, len(pool), 40):
        ids = [a["id"] for a in pool[i:i + 40]]
        rows, _ = client.call("GET", "/api/v1/accounts/relationships", {"id[]": ids})
        rel.update({r["id"]: r for r in rows})
    picks = pick(pool, me["id"], ledger, rel, max_follows)
    log(f"{len(pool)} candidates, {len(picks)} to follow (max {max_follows})")
    followed = []
    for n, acct in enumerate(picks):
        if dry_run:
            log(f"would follow @{acct.get('acct')}")
            continue
        if n:
            sleep(pause)
        try:
            _, headers = client.call("POST", f"/api/v1/accounts/{acct['id']}/follow")
        except RateLimited as e:
            log(f"rate limited (reset {e}); stopping")
            break
        except urllib.error.HTTPError as e:
            log(f"follow @{acct.get('acct')} failed: HTTP {e.code}; skipping")
            ledger.add(acct["id"])
            continue
        ledger.add(acct["id"])
        followed.append(acct.get("acct"))
        log(f"followed @{acct.get('acct')}")
        remaining = headers.get("X-RateLimit-Remaining")
        if remaining is not None and remaining.isdigit() and int(remaining) <= reserve:
            log(f"only {remaining} follows left today; stopping to keep {reserve} for manual use")
            break
    return followed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max", type=int, default=42, help="follows per run")
    ap.add_argument("--reserve", type=int, default=50, help="stop when this many daily follows remain")
    ap.add_argument("--ledger", default=".mastodon-follow/ledger.json")
    ap.add_argument("--tags", default=",".join(TAGS), help="comma-separated hashtags, without #")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not 0 < a.max <= 42:
        sys.exit("--max must be 1-42")
    token = os.environ.get("MASTODON_TOKEN")
    if not token:
        sys.exit("MASTODON_TOKEN is not set")
    ledger = load_ledger(a.ledger)
    try:
        tags = [t.strip().lstrip("#") for t in a.tags.split(",") if t.strip()]
        followed = run(Client(token), ledger, a.max, a.reserve, a.dry_run, tags=tags)
    finally:
        if not a.dry_run:
            save_ledger(a.ledger, ledger)
    print(f"followed {len(followed)}: " + " ".join("@" + x for x in followed if x))


if __name__ == "__main__":
    main()
