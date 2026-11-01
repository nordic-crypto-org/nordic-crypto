#!/usr/bin/env python3
"""Post each new Nordic Crypto newsletter issue to X (@nordiccryptobot) as ONE long post (X Premium) with the newsreel video, once.

Post: "Nordic Crypto #N: <headline>" and the issue link, then each story's headline and its nordiccrypto.no story page
(https://nordiccrypto.no/stories/<id>/, never the original source). X caps the links in one post, so past MAX_URLS
the remaining headlines are listed without a link. No thread: if X rejects the post, the run fails and nothing is posted.

Source: newsletter/published/issues.json and newsletter/published/<id>/issue.html; story ids from data/news.json and
archive/articles.json, matched on the source URL. The video is the local newsletter/published/<id>/video.mp4 when
present, otherwise video.url from issues.json (checked against video.sha256). Before a real post the issue page and
every story page must answer 200.

State: data/x_posted.json maps issue id -> {"posted_at", "tweet_ids", "mode"}. A posted issue is never posted again.

Secrets (env, never printed): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET (OAuth 1.0a user context of
@nordiccryptobot, app with Read and Write). If any is missing the script logs one line and exits 0 without posting.

  python3 tools/x_newsletter.py [--issue 002] [--dry-run] [--state data/x_posted.json] [--no-video]
Without --issue the newest issue in issues.json is used.
"""
import argparse, base64, datetime as dt, hashlib, hmac, html, json, os, re, secrets, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISHED = os.path.join(ROOT, "newsletter", "published")
STATE = os.path.join(ROOT, "data", "x_posted.json")
SITE = "https://nordiccrypto.no"
UPLOAD = "https://api.x.com/2/media/upload"
TWEETS = "https://api.x.com/2/tweets"
UA = "nordic-crypto-x-newsletter/1 (+https://nordiccrypto.no/)"
LIMIT, URL_LEN = 280, 23
LONG_LIMIT = 25000  # X Premium long posts
MAX_URLS = 20  # issue #1 went out with 20 links; #3 with 64 was refused ("exceeds the number of allowed URLs")
CHUNK = 4 * 1024 * 1024
ENV = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
URL_RE = re.compile(r"https?://\S+")


def log(msg):
    print(f"[x-newsletter] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- text
def x_len(text):
    """Length as X counts it: every URL is 23 characters."""
    n, last = 0, 0
    for m in URL_RE.finditer(text):
        n += len(text[last:m.start()]) + URL_LEN
        last = m.end()
    return n + len(text[last:])


# ---------------------------------------------------------------- issue
def strip_tags(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())


STORY_RE = re.compile(r'<p[^>]*>\s*<a href="(?P<url>https?://[^"]+)"[^>]*font-weight:bold[^>]*>(?P<title>.*?)</a>(?P<rest>.*?)</p>', re.S)


def parse_stories(issue_html):
    out = []
    issue_html = issue_html.replace('__SITE__/', SITE + '/')   # own stories link via the site placeholder
    for m in STORY_RE.finditer(issue_html):
        segs = re.split(r"<br\s*/?>", m.group("rest"))
        summary = strip_tags(segs[1]) if len(segs) > 1 else ""
        out.append({"title": strip_tags(m.group("title")), "summary": summary, "url": m.group("url")})
    return out


def load_issue(issue_id=None):
    with open(os.path.join(PUBLISHED, "issues.json"), encoding="utf-8") as fh:
        issues = json.load(fh)["issues"]
    if issue_id is None:
        meta = max(issues, key=lambda i: (i.get("date", ""), i["id"]))
    else:
        issue_id = issue_id.zfill(3)
        meta = next((i for i in issues if i["id"] == issue_id), None)
        if not meta:
            raise SystemExit(f"issue {issue_id} not in newsletter/published/issues.json")
    with open(os.path.join(PUBLISHED, meta["id"], "issue.html"), encoding="utf-8") as fh:
        meta = dict(meta, stories_list=parse_stories(fh.read()))
    return meta


def issue_url(meta):
    return f"{SITE}/newsletter/{meta['id']}/"


def _key(url):
    u = re.sub(r"^https?://(www\.)?", "", (url or "").strip().lower())
    return u.rstrip("/")


def story_index():
    """Source URL -> our story page, from data/news.json and archive/articles.json."""
    idx = {}
    def add(url, page):
        if url and str(url).startswith("http"):
            idx.setdefault(_key(url), page)
    for path, key in ((os.path.join(ROOT, "data", "news.json"), "items"), (os.path.join(ROOT, "archive", "articles.json"), "articles")):
        try:
            with open(path, encoding="utf-8") as fh:
                rows = json.load(fh).get(key, [])
        except FileNotFoundError:
            continue
        for i in rows:
            if not i.get("id"):
                continue
            u = i.get("url") or ""
            page = f"{SITE}/{u.lstrip('/')}" if i.get("own_story") and u and not u.startswith("http") else f"{SITE}/stories/{i['id']}/"
            for src in [u, i.get("canonical_url")] + [l.get("url") if isinstance(l, dict) else l for l in i.get("links") or []]:
                add(src, page)
    return idx


def story_pages(meta, idx=None):
    """Our story page for each story in the issue (None when it cannot be found)."""
    idx = story_index() if idx is None else idx
    return [s["url"] if s["url"].startswith(SITE + "/") else idx.get(_key(s["url"])) for s in meta["stories_list"]]


def build_long_post(meta, pages):
    """Header with the issue link, then each headline with its story page."""
    n = meta.get("number") or int(meta["id"])
    title = re.sub(rf"^Nordic Crypto #{n}:\s*", "", meta["title"])
    blocks, rest = [f"Nordic Crypto #{n}: {title}\n{issue_url(meta)}"], []
    links = 1
    for s, page in zip(meta["stories_list"], pages):
        if page and links < MAX_URLS:
            blocks.append(f"{s['title']}\n{page}")
            links += 1
        else:
            rest.append(s["title"])
    if rest:
        blocks.append("More in the issue:\n" + "\n".join(rest))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------- state
def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def save_state(path, state):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- X API
def _pct(s):
    return urllib.parse.quote(str(s), safe="~-._")


def oauth_header(method, url, creds, params=None):
    """OAuth 1.0a HMAC-SHA1. params = query/form params that are part of the signature (not JSON or multipart)."""
    key, secret, token, token_secret = creds
    oauth = {"oauth_consumer_key": key, "oauth_nonce": secrets.token_hex(16), "oauth_signature_method": "HMAC-SHA1",
             "oauth_timestamp": str(int(time.time())), "oauth_token": token, "oauth_version": "1.0"}
    allp = dict(params or {}, **oauth)
    pstr = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted((_pct(k), _pct(v)) for k, v in allp.items()))
    base = "&".join([method.upper(), _pct(url), _pct(pstr)])
    sig = base64.b64encode(hmac.new(f"{_pct(secret)}&{_pct(token_secret)}".encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))


def _call(req):
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"X API {req.get_method()} {req.full_url.split('?')[0]} -> {e.code}: {e.read()[:500].decode('utf-8', 'replace')}")


def x_form(creds, url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": oauth_header("POST", url, creds, params), "Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA})
    return _call(req)


def x_get(creds, url, params):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={
        "Authorization": oauth_header("GET", url, creds, params), "User-Agent": UA})
    return _call(req)


def x_json(creds, url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={
        "Authorization": oauth_header("POST", url, creds), "Content-Type": "application/json", "User-Agent": UA})
    return _call(req)


def upload_video(creds, path):
    """v2 chunked upload: initialize, append (4 MB segments), finalize, then poll status until processing succeeds.
    (The v1.1 upload.twitter.com endpoint answers 401 for pay-per-use apps.)"""
    size = os.path.getsize(path)
    mid = x_json(creds, UPLOAD + "/initialize", {"media_type": "video/mp4", "total_bytes": size, "media_category": "tweet_video"})["data"]["id"]
    log(f"initialize media {mid} ({size} bytes)")
    url = f"{UPLOAD}/{mid}/append"
    with open(path, "rb") as fh:
        seg = 0
        while chunk := fh.read(CHUNK):
            boundary = "nc" + secrets.token_hex(12)
            body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"segment_index\"\r\n\r\n{seg}\r\n"
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"media\"; filename=\"blob\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode() \
                + chunk + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(url, data=body, method="POST", headers={
                "Authorization": oauth_header("POST", url, creds), "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": UA})
            _call(req)
            seg += 1
    log(f"append {seg} segments")
    info = x_json(creds, f"{UPLOAD}/{mid}/finalize", {}).get("data", {}).get("processing_info")
    deadline = time.time() + 600
    while info and info.get("state") in ("pending", "in_progress"):
        if time.time() > deadline:
            raise RuntimeError("video processing timed out")
        time.sleep(max(1, int(info.get("check_after_secs", 5))))
        info = x_get(creds, UPLOAD, {"command": "STATUS", "media_id": mid}).get("data", {}).get("processing_info")
        log(f"status {info and info.get('state')} {info and info.get('progress_percent', '')}")
    if info and info.get("state") == "failed":
        raise RuntimeError(f"video processing failed: {info.get('error')}")
    return mid


def create_post(creds, text, reply_to=None, media_id=None):
    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    if media_id:
        payload["media"] = {"media_ids": [media_id]}
    req = urllib.request.Request(TWEETS, data=json.dumps(payload).encode(), method="POST", headers={
        "Authorization": oauth_header("POST", TWEETS, creds), "Content-Type": "application/json", "User-Agent": UA})
    return _call(req)["data"]["id"]


# ---------------------------------------------------------------- video / liveness
def fetch_video(meta):
    v = meta.get("video") or {}
    local = os.path.join(PUBLISHED, meta["id"], v.get("file", "video.mp4"))
    if os.path.exists(local):
        return local
    if not v.get("url"):
        return None
    dst = os.path.join(tempfile.gettempdir(), f"nordic-crypto-{meta['id']}-video.mp4")
    log(f"downloading {v['url']}")
    req = urllib.request.Request(v["url"], headers={"User-Agent": UA})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=300) as r, open(dst, "wb") as fh:
        while b := r.read(1 << 20):
            h.update(b); fh.write(b)
    if v.get("sha256") and h.hexdigest() != v["sha256"]:
        raise RuntimeError(f"video sha256 mismatch for issue {meta['id']}")
    return dst


def is_live(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--issue", help="issue id, e.g. 002 (default: newest)")
    ap.add_argument("--dry-run", action="store_true", help="print the post, post nothing, leave the state file alone")
    ap.add_argument("--state", default=STATE)
    ap.add_argument("--no-video", action="store_true", help="post without the video")
    a = ap.parse_args(argv)

    meta = load_issue(a.issue)
    pages = story_pages(meta)
    post = build_long_post(meta, pages)
    missing_pages = [s["title"] for s, p in zip(meta["stories_list"], pages) if not p]
    state = load_state(a.state)
    done = state.get(meta["id"], {})
    has_video = bool(meta.get("video")) and not a.no_video

    if a.dry_run:
        print(f"# Issue {meta['id']} ({meta['date']}): one long post, {x_len(post)}/{LONG_LIMIT} chars, "
              f"{len(URL_RE.findall(post))}/{MAX_URLS} links{' + video' if has_video else ''}"
              f"{' [already posted, a real run would skip]' if done.get('complete') else ''}")
        for t in missing_pages:
            print(f"# no story page found: {t}")
        print(f"\n{post}{chr(10) + '[+ video.mp4]' if has_video else ''}")
        return 0

    if done.get("complete"):
        log(f"issue {meta['id']} already posted ({done.get('posted_at')}); nothing to do")
        return 0
    if missing_pages:
        log(f"no story page for: {'; '.join(missing_pages)}")
        return 1
    missing = [k for k in ENV if not os.environ.get(k)]
    if missing:
        log(f"skipping: missing {', '.join(missing)}")
        return 0
    creds = tuple(os.environ[k] for k in ENV)
    for url in [issue_url(meta)] + URL_RE.findall(post)[1:]:
        if not is_live(url):
            log(f"skipping: {url} is not live yet")
            return 0

    media_id = None
    if has_video:
        path = fetch_video(meta)
        if path:
            media_id = upload_video(creds, path)
    tid = create_post(creds, post, media_id=media_id)
    state[meta["id"]] = {"tweet_ids": [tid], "complete": True, "mode": "long",
                         "posted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                         "url": f"https://x.com/nordiccryptobot/status/{tid}"}
    save_state(a.state, state)
    log(f"done: https://x.com/nordiccryptobot/status/{tid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
