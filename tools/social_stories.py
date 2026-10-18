#!/usr/bin/env python3
"""Post new Nordic Crypto stories to Bluesky and Threads, in English.

  bluesky  one post per new story: flag + English headline + story link, with a link card (300 characters)
  threads  one digest per Oslo day, like X: header, then flag + headline + link per story; a thread past 500 characters

Stories come from the live /api/v1/news.json (published in the last 48 h, after the state's "since"). A story is ready
when its headline and summary are in every site language (as tools/story_translate.py plans them) and
https://nordiccrypto.no/stories/<id>/ answers 200. Bluesky posts a ready story at once (an untranslated one after 12 h);
Threads waits for all, and from --deadline-hour (Oslo) posts the ready ones. No state file: record "since" = now and
post nothing, so a lost state never floods. A story is recorded only after the post went through.

Secrets (env, never printed): BLUESKY_HANDLE + BLUESKY_APP_PASSWORD (optional BLUESKY_PDS), THREADS_USER_ID +
THREADS_ACCESS_TOKEN (threads_basic, threads_content_publish). Missing: one line, exit 0, state unchanged.

  python3 tools/social_stories.py bluesky|threads --state PATH [--dry-run] [--feed URL_OR_PATH] [--now ISO]
"""
import argparse, datetime as dt, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headlines, telegram_events as te
import x_newsletter as xn

STORY = "https://nordiccrypto.no/stories/{}/"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
UA = "nordic-crypto-social/1 (+https://nordiccrypto.no/)"
URL_RE = re.compile(r"https?://\S+")
BSKY_LIMIT, THREADS_LIMIT, THREADS_LINKS = 300, 500, 5
GRACE = dt.timedelta(hours=12)
ENV = {"bluesky": ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"), "threads": ("THREADS_USER_ID", "THREADS_ACCESS_TOKEN")}


def log(kind, msg):
    print(f"[{kind}] {msg}", file=sys.stderr, flush=True)


def en_title(e):
    return " ".join(str(e.get("title_en") or (e.get("title_i18n") or {}).get("en") or e.get("title") or "").split())


def untranslated(e):
    have = headlines.title_map(e, {})
    miss = {l for l in headlines.needed_langs(e.get("language")) if not have.get(l)}
    if (e.get("summary") or "").strip():
        miss |= {l for l in headlines.TRANSLATED if not ((e.get("summary_i18n") or {}).get(l) or "").strip()}
    return sorted(miss)


def bsky_len(s):   # code points >= graphemes, so this never undercounts
    return len(unicodedata.normalize("NFC", s))


def threads_len(s):   # Threads counts emoji as UTF-8 bytes
    return sum(1 if ord(c) < 0x2000 else len(c.encode()) for c in unicodedata.normalize("NFC", s))


def flag(e):
    return te.FLAGS.get((e.get("country") or "").upper(), "📰")


def fit(head, url, limit, size):
    """'head\\nurl' within limit, cutting head at a word."""
    while size(f"{head}\n{url}") > limit and len(head) > 10:
        head = (head.rsplit(" ", 1)[0] if " " in head[:-1] else head[:-2]).rstrip(",;:–-…") + "…"
    return f"{head}\n{url}"


def candidates(items, now, since, done):
    out = [e for e in items if e.get("id") and en_title(e) and e["id"] not in done
           and (p := te.parse(e.get("published"))) and max(since, now - dt.timedelta(hours=48)) <= p <= now]
    return sorted(out, key=lambda e: (te.parse(e["published"]), e["id"]))


def http_json(req, secret=""):
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace")[:400]
        raise RuntimeError(f"HTTP {err.code} {body.replace(secret, '***') if secret else body}") from None


# ---------------------------------------------------------------- Bluesky
def bsky_post_record(e):
    url = e.get("html_url") or STORY.format(e["id"])
    text = fit(f"{flag(e)} {en_title(e)}", url, BSKY_LIMIT, bsky_len)
    b = text.encode()
    start = b.rindex(url.encode())
    rec = {"$type": "app.bsky.feed.post", "text": text, "langs": ["en"],
           "facets": [{"index": {"byteStart": start, "byteEnd": start + len(url.encode())},
                       "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]}],
           "embed": {"$type": "app.bsky.embed.external",
                     "external": {"uri": url, "title": en_title(e)[:300], "description": (e.get("summary") or "")[:300]}}}
    return rec


class Bluesky:
    def __init__(self, handle, password, pds=None):
        self.pds = (pds or "https://bsky.social").rstrip("/")
        s = self.call("com.atproto.server.createSession", {"identifier": handle, "password": password}, secret=password)
        self.jwt, self.did, self.handle, self.thumb = s["accessJwt"], s["did"], s.get("handle", handle), None

    def call(self, method, body=None, data=None, ctype="application/json", secret=""):
        h = {"User-Agent": UA, "Content-Type": ctype}
        if getattr(self, "jwt", None):
            h["Authorization"] = "Bearer " + self.jwt
        req = urllib.request.Request(f"{self.pds}/xrpc/{method}", data if data is not None else json.dumps(body).encode(), h)
        return http_json(req, secret or getattr(self, "jwt", ""))

    def card_thumb(self, page_url):
        """The story page's og:image (the brand card), uploaded once per run; none if anything fails."""
        if self.thumb is None:
            self.thumb = False
            try:
                req = urllib.request.Request(page_url, headers={"User-Agent": UA})
                html = urllib.request.urlopen(req, timeout=30).read().decode(errors="replace")
                m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                if m:
                    r = urllib.request.urlopen(urllib.request.Request(m.group(1), headers={"User-Agent": UA}), timeout=30)
                    img, ctype = r.read(), r.headers.get("Content-Type", "image/png")
                    if len(img) < 950_000:
                        self.thumb = self.call("com.atproto.repo.uploadBlob", data=img, ctype=ctype)["blob"]
            except Exception as err:
                log("bluesky", f"no card image: {type(err).__name__}")
        return self.thumb or None

    def post(self, rec):
        rec = dict(rec, createdAt=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        thumb = self.card_thumb(rec["embed"]["external"]["uri"])
        if thumb:
            rec["embed"]["external"]["thumb"] = thumb
        out = self.call("com.atproto.repo.createRecord", {"repo": self.did, "collection": "app.bsky.feed.post", "record": rec})
        return out["uri"], f"https://bsky.app/profile/{self.handle}/post/{out['uri'].rsplit('/', 1)[-1]}"


def run_bluesky(feed, state_path, now, *, dry, client=None, live=xn.is_live, max_posts=4):
    state = xn.load_state(state_path)
    if not state:
        if not dry:
            xn.save_state(state_path, {"since": now.isoformat(timespec="seconds"), "posted": {}})
            log("bluesky", "no state yet; tracking stories from now, posted nothing"); return 0
        state = {"since": (now - dt.timedelta(hours=24)).isoformat()}
    posted = state.setdefault("posted", {})
    todo = []
    for e in candidates(feed.get("items") or [], now, te.parse(state["since"]), posted):
        miss = untranslated(e)
        if miss and now - te.parse(e["published"]) < GRACE:
            log("bluesky", f"{e['id']}: waiting for {','.join(miss)}"); continue
        if not live(e.get("html_url") or STORY.format(e["id"])):
            log("bluesky", f"{e['id']}: page not live yet"); continue
        todo.append(e)
    if not todo:
        log("bluesky", "nothing new"); return 0
    for e in todo[:max_posts]:
        rec = bsky_post_record(e)
        if dry:
            print(f"--- {e['id']} ({bsky_len(rec['text'])}/{BSKY_LIMIT})\n{rec['text']}\n"); continue
        uri, url = client.post(rec)
        posted[e["id"]] = {"uri": uri, "url": url, "at": now.isoformat(timespec="seconds")}
        xn.save_state(state_path, state); log("bluesky", f"posted {e['id']}: {url}")
        time.sleep(3)
    left = len(todo) - min(len(todo), max_posts)
    if left:
        log("bluesky", f"{left} left for the next run")
    return 0


# ---------------------------------------------------------------- Threads
def header(day):
    return f"📰 New on Nordic Crypto – {day.day} {MONTHS[day.month - 1]} {day.year}"


def build_digest(stories, day):
    posts, cur, links = [], header(day), 0
    for e in stories:
        line = fit(f"{flag(e)} {en_title(e)}", e.get("html_url") or STORY.format(e["id"]), THREADS_LIMIT - 60, threads_len)
        if threads_len(cur + "\n\n" + line) > THREADS_LIMIT or links >= THREADS_LINKS:
            posts.append(cur); cur, links = line, 1
        else:
            cur += "\n\n" + line; links += 1
    return posts + [cur]


class Threads:
    API = "https://graph.threads.net/v1.0"

    def __init__(self, user_id, token):
        self.uid, self.token = user_id, token

    def call(self, path, params=None, method="POST"):
        p = urllib.parse.urlencode(dict(params or {}, access_token=self.token))
        req = (urllib.request.Request(f"{self.API}/{path}?{p}", headers={"User-Agent": UA}) if method == "GET" else
               urllib.request.Request(f"{self.API}/{path}", p.encode(), {"User-Agent": UA}))
        return http_json(req, self.token)

    def post(self, text, reply_to=None):
        p = {"media_type": "TEXT", "text": text}
        if m := URL_RE.search(text):
            p["link_attachment"] = m.group(0)
        if reply_to:
            p["reply_to_id"] = reply_to
        c = self.call(f"{self.uid}/threads", p)["id"]
        for _ in range(20):
            st = self.call(c, {"fields": "status,error_message"}, "GET")
            if st.get("status") == "FINISHED":
                break
            if st.get("status") in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {st}")
            time.sleep(3)
        return self.call(f"{self.uid}/threads_publish", {"creation_id": c})["id"]

    def permalink(self, media_id):
        try:
            return self.call(media_id, {"fields": "permalink"}, "GET").get("permalink")
        except RuntimeError:
            return None


def run_threads(feed, state_path, now, *, dry, client=None, live=xn.is_live, deadline_hour=18):
    day = now.astimezone(te.OSLO); key = day.date().isoformat()
    state = xn.load_state(state_path)
    if not state:
        if not dry:
            xn.save_state(state_path, {"since": now.isoformat(timespec="seconds")})
            log("threads", "no state yet; tracking stories from now, posted nothing"); return 0
        state = {"since": (now - dt.timedelta(hours=24)).isoformat()}
    days = {k: v for k, v in state.items() if k != "since"}
    done = days.get(key, {})
    if done.get("complete"):
        log("threads", f"{key} already posted ({done.get('url')})"); return 0
    waiting = {}
    if done.get("story_ids"):
        byid = {e.get("id"): e for e in feed.get("items") or []}
        stories = [byid[i] for i in done["story_ids"] if i in byid]
    else:
        seen = {i for k, v in days.items() if k != key for i in v.get("story_ids", [])}
        deferred = {i for v in days.values() for i in v.get("deferred", [])}
        stories = []
        for e in candidates(feed.get("items") or [], now, te.parse(state["since"]), seen):
            miss = untranslated(e)
            if miss or not live(e.get("html_url") or STORY.format(e["id"])):
                waiting[e["id"]] = "untranslated: " + ",".join(miss) if miss else "page not live"
            else:
                stories.append(e)
        why = "; ".join(f"{i} ({w})" for i, w in waiting.items())
        if set(waiting) - deferred and day.hour < deadline_hour:
            log("threads", f"{key}: waiting for {why}"); return 0
        if waiting:
            log("threads", f"{key}: posting without {why}")
    if not stories:
        if waiting and not dry:
            state[key] = {"deferred": sorted(waiting), "complete": False}; xn.save_state(state_path, state)
        log("threads", f"{key}: no new stories ready"); return 0
    posts = build_digest(stories, day)
    if dry:
        for i, p in enumerate(posts, 1):
            print(f"--- {i}/{len(posts)} ({threads_len(p)}/{THREADS_LIMIT})\n{p}\n")
        return 0
    ids = list(done.get("post_ids", []))
    entry = {"story_ids": [e["id"] for e in stories], "post_ids": ids, "complete": False}
    if waiting:
        entry["deferred"] = sorted(waiting)
    for i, text in enumerate(posts):
        if i < len(ids):
            continue
        ids.append(client.post(text, reply_to=ids[-1] if ids else None))
        state[key] = entry; xn.save_state(state_path, state)
        log("threads", f"posted {i + 1}/{len(posts)}: {ids[-1]}")
    entry.update(complete=True, posted_at=now.isoformat(timespec="seconds"), url=client.permalink(ids[0]))
    state[key] = entry; xn.save_state(state_path, state)
    log("threads", f"done: {entry['url'] or ids[0]}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kind", choices=("bluesky", "threads"))
    ap.add_argument("--state", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--feed", default=te.NEWS_FEED)
    ap.add_argument("--now")
    ap.add_argument("--deadline-hour", type=int, default=18)
    a = ap.parse_args(argv)
    now = te.parse(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    creds = [os.environ.get(k, "") for k in ENV[a.kind]]
    if not all(creds) and not a.dry_run:
        log(a.kind, f"skipping: {' / '.join(ENV[a.kind])} not set"); return 0
    feed = te.load_feed(a.feed)
    if feed.get("preview"):
        log(a.kind, "refusing a preview feed"); return 2
    if a.kind == "bluesky":
        client = None if a.dry_run else Bluesky(*creds, os.environ.get("BLUESKY_PDS"))
        return run_bluesky(feed, a.state, now, dry=a.dry_run, client=client)
    client = None if a.dry_run else Threads(*creds)
    return run_threads(feed, a.state, now, dry=a.dry_run, client=client, deadline_hour=a.deadline_hour)


if __name__ == "__main__":
    sys.exit(main())
