#!/usr/bin/env python3
"""Post each new Nordic Crypto newsletter issue to X (@nordiccryptobot) as ONE long post, once.

Post: "Nordic Crypto #N: <headline>" and the issue link, then every story's headline and its nordiccrypto.no
page (https://nordiccrypto.no/stories/<id>/, never the original source). Every story is linked. A post that
does not fit X's long-post character limit fails; stories are not dropped to make it fit. No thread: if X
rejects the post, the run fails and nothing is posted.

The post attaches one generated image of the issue (tools/story_images.py): a style that is not already in
the library, «Nordic Crypto» in the top-right, no outlet logos. The PNG is stored in R2 and the row in D1,
not in git. X allows one video or up to four images, not both, so the newsreel is not attached on the same
post. It is still downloaded (GitHub API when GH_TOKEN is set, with retry/backoff on 502) and checked
against video.sha256. The issue page linked at the top has the newsreel.

State: data/x_posted.json. An issue with complete, tweet_ids or url is never posted again.

Secrets (env, never printed): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET. The token's user
must be @nordiccryptobot; @jQrgensn and any other account are refused. If an X secret is missing the script
logs one line and exits 0 without posting.

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
# Kept for tools/x_feed.py digests. The newsletter post does not use it: every story is linked,
# and a post that does not fit LONG_LIMIT fails instead of listing headlines with the link removed.
MAX_URLS = 20
ALLOWED_ACCOUNT = "nordiccryptobot"
RETRYABLE = {429, 500, 502, 503, 504}
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
    """Header with the issue link, then every headline with its story page.

    A missing page or a link off nordiccrypto.no raises. Over LONG_LIMIT raises.
    Stories are not dropped and are not listed without their link.
    """
    n = meta.get("number") or int(meta["id"])
    title = re.sub(rf"^Nordic Crypto #{n}:\s*", "", meta["title"])
    stories = meta["stories_list"]
    if len(pages) != len(stories):
        raise RuntimeError("story pages do not line up with the issue")
    blocks = [f"Nordic Crypto #{n}: {title}\n{issue_url(meta)}"]
    for s, page in zip(stories, pages):
        if not page or not str(page).startswith(SITE + "/"):
            raise RuntimeError(f"no nordiccrypto.no page for «{s['title']}»; refusing to list it without a link")
        blocks.append(f"{s['title']}\n{page}")
    text = "\n\n".join(blocks)
    for u in URL_RE.findall(text):
        if not u.startswith(SITE + "/"):
            raise RuntimeError(f"refusing a link off nordiccrypto.no: {u}")
    if x_len(text) > LONG_LIMIT:
        raise RuntimeError(
            f"long post is {x_len(text)} characters, over X's long-post limit of {LONG_LIMIT}; "
            f"refusing to drop any of the {len(stories)} stories to make it fit")
    return text


# ---------------------------------------------------------------- state
def already_posted(state, issue_id):
    """True when x_posted.json already has this issue. A partial row counts, so a retry cannot double-post."""
    row = (state or {}).get(issue_id)
    if not isinstance(row, dict):
        return False
    return bool(row.get("complete") or row.get("tweet_ids") or row.get("url"))


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


def upload_image(creds, path):
    """v2 simple upload for a PNG or JPEG. Returns the media id."""
    with open(path, "rb") as fh:
        data = fh.read()
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    mid = x_json(creds, UPLOAD + "/initialize", {
        "media_type": mime, "total_bytes": len(data), "media_category": "tweet_image",
    })["data"]["id"]
    log(f"initialize image {mid} ({len(data)} bytes)")
    url = f"{UPLOAD}/{mid}/append"
    boundary = "nc" + secrets.token_hex(12)
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"segment_index\"\r\n\r\n0\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"media\"; filename=\"card{ext}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": oauth_header("POST", url, creds),
        "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": UA})
    _call(req)
    x_json(creds, f"{UPLOAD}/{mid}/finalize", {})
    return mid


def account_username(creds):
    """Username of the token. Used to refuse every account except @nordiccryptobot."""
    data = x_get(creds, "https://api.x.com/2/users/me", {"user.fields": "username"})
    return ((data.get("data") or {}).get("username") or "").strip()


def assert_brand_account(creds):
    name = account_username(creds)
    if name.lower() != ALLOWED_ACCOUNT:
        raise RuntimeError(f"refusing to post as @{name or 'unknown'}; only @{ALLOWED_ACCOUNT} may post the newsletter")
    log(f"posting as @{ALLOWED_ACCOUNT}")
    return name


def create_post(creds, text, reply_to=None, media_id=None, media_ids=None):
    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    ids = [i for i in (media_ids or []) if i]
    if media_id and media_id not in ids:
        ids.insert(0, media_id)
    if ids:
        payload["media"] = {"media_ids": ids[:4]}
    req = urllib.request.Request(TWEETS, data=json.dumps(payload).encode(), method="POST", headers={
        "Authorization": oauth_header("POST", TWEETS, creds), "Content-Type": "application/json", "User-Agent": UA})
    return _call(req)["data"]["id"]


# ---------------------------------------------------------------- video / liveness
def _drain(err):
    try:
        err.close()
    except Exception:
        pass


def _redact(text):
    out = str(text)
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
                "YT_REFRESH_TOKEN", "YT_CLIENT_SECRET", "CF_AI_TOKEN", "CLOUDFLARE_API_TOKEN"):
        val = os.environ.get(key)
        if val and len(val) > 6 and val in out:
            out = out.replace(val, "[secret]")
    return out


def _urlopen(req, timeout):
    return urllib.request.urlopen(req, timeout=timeout)


def _read_response(req, opener, timeout, redirects=4):
    try:
        with opener(req, timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and redirects:
            loc = e.headers.get("Location") if getattr(e, "headers", None) else None
            _drain(e)
            if not loc:
                raise
            nxt = urllib.request.Request(urllib.parse.urljoin(req.full_url, loc), headers={"User-Agent": UA})
            return _read_response(nxt, opener, timeout, redirects - 1)
        raise


def release_parts(url):
    """owner, repo, tag, filename for a GitHub release download URL, else None."""
    parts = urllib.parse.urlparse(url).path.strip("/").split("/")
    if len(parts) >= 6 and parts[2] == "releases" and parts[3] == "download":
        return parts[0], parts[1], urllib.parse.unquote(parts[4]), urllib.parse.unquote(parts[5])
    return None


def _github_asset(parsed, token, opener):
    owner, repo, tag, fname = parsed
    meta_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag)}"
    headers = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
               "User-Agent": UA, "X-GitHub-Api-Version": "2022-11-28"}
    meta = json.loads(_read_response(urllib.request.Request(meta_url, headers=headers), opener, 60).decode("utf-8"))
    asset = next((a for a in meta.get("assets") or [] if a.get("name") == fname), None)
    if not asset or not asset.get("url"):
        raise RuntimeError(f"release {tag} has no asset named {fname}")
    headers = {"Authorization": "Bearer " + token, "Accept": "application/octet-stream", "User-Agent": UA}
    return _read_response(urllib.request.Request(asset["url"], headers=headers), opener, 300)


def download_url(url, dest, *, token=None, attempts=5, sleep=time.sleep, opener=None):
    """Write url to dest. A release asset uses the GitHub API when token is set.

    The public release host often answers 502 or 504 from a runner (run 42474108181).
    Those, plus 429/500/503, are retried with backoff. The token is never logged.
    """
    opener = opener or _urlopen
    parsed = release_parts(url)
    delay = 2
    last = None
    api_token = token or None
    for attempt in range(1, attempts + 1):
        if parsed and api_token:
            try:
                data = _github_asset(parsed, api_token, opener)
                with open(dest, "wb") as fh:
                    fh.write(data)
                return dest
            except urllib.error.HTTPError as e:
                last = e
                code = e.code
                _drain(e)
                log(f"release API HTTP {code} (attempt {attempt}/{attempts})")
                if code not in RETRYABLE:
                    api_token = None
            except Exception as e:
                last = e
                log("release API failed (" + _redact(f"{type(e).__name__}: {e}")[:200] + ")")
        try:
            data = _read_response(urllib.request.Request(url, headers={"User-Agent": UA}), opener, 300)
            with open(dest, "wb") as fh:
                fh.write(data)
            return dest
        except urllib.error.HTTPError as e:
            last = e
            code = e.code
            _drain(e)
            if code not in RETRYABLE or attempt == attempts:
                raise
            log(f"release download HTTP {code} (attempt {attempt}/{attempts}), retrying in {delay}s")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt == attempts:
                raise
            log(f"release download failed ({type(e).__name__}, attempt {attempt}/{attempts}), retrying in {delay}s")
        sleep(delay)
        delay *= 2
    if last:
        raise last
    raise RuntimeError("release download failed")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_video(meta, *, token=None, attempts=5, sleep=time.sleep, opener=None):
    v = meta.get("video") or {}
    local = os.path.join(PUBLISHED, meta["id"], v.get("file", "video.mp4"))
    if os.path.exists(local):
        if v.get("sha256") and _sha256_file(local) != v["sha256"]:
            raise RuntimeError(f"video sha256 mismatch for issue {meta['id']}")
        return local
    if not v.get("url"):
        return None
    dst = os.path.join(tempfile.gettempdir(), f"nordic-crypto-{meta['id']}-video.mp4")
    log(f"downloading {v['url']}")
    if token is None:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    download_url(v["url"], dst, token=token or None, attempts=attempts, sleep=sleep, opener=opener)
    if v.get("sha256") and _sha256_file(dst) != v["sha256"]:
        try:
            os.unlink(dst)
        except OSError:
            pass
        raise RuntimeError(f"video sha256 mismatch for issue {meta['id']}")
    return dst


def _drop_temp(path):
    if not path:
        return
    real = os.path.realpath(path)
    root = os.path.realpath(ROOT) + os.sep
    tmp = os.path.realpath(tempfile.gettempdir()) + os.sep
    if real.startswith(root) or not real.startswith(tmp):
        return
    try:
        os.unlink(real)
    except OSError:
        pass


def prepare_issue_image(meta):
    """Generate or reuse the issue illustration in R2/D1. Returns a dict with a local PNG path."""
    import story_images
    gaps = story_images.storage_gaps()
    if gaps:
        raise RuntimeError(
            "issue image is not stored (" + ", ".join(gaps) + " missing). "
            "The picture belongs in R2 and D1, not in git. "
            "Set the same Cloudflare variables as the Story illustrations workflow.")
    store = story_images.open_store()
    info = story_images.generate_issue_image(meta, store, now=dt.datetime.now(dt.timezone.utc))
    if info.get("kind") != "ai" or not info.get("url"):
        raise RuntimeError("issue image was not generated; not posting")
    if not info.get("path"):
        fd, path = tempfile.mkstemp(prefix="nc-issue-", suffix=".png")
        os.close(fd)
        download_url(info["url"], path, token=None)
        info = dict(info, path=path)
    log(f"issue image {info.get('style_id')} {info.get('url')}")
    return info


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
    ap.add_argument("--no-video", action="store_true", help="do not download or check the newsreel")
    a = ap.parse_args(argv)

    meta = load_issue(a.issue)
    pages = story_pages(meta)
    try:
        post = build_long_post(meta, pages)
    except RuntimeError as err:
        log(str(err))
        return 1
    state = load_state(a.state)
    has_video = bool(meta.get("video")) and not a.no_video
    posted = already_posted(state, meta["id"])

    if a.dry_run:
        print(f"# Issue {meta['id']} ({meta['date']}): one long post, {x_len(post)}/{LONG_LIMIT} chars, "
              f"{len(URL_RE.findall(post))} links, one image"
              f"{' [already posted, a real run would skip]' if posted else ''}")
        note = "\n[+ issue image"
        if has_video:
            note += "; newsreel checked, not attached on X]"
        else:
            note += "]"
        print(f"\n{post}{note}")
        return 0

    if posted:
        row = state.get(meta["id"]) or {}
        log(f"issue {meta['id']} already in x_posted.json ({row.get('url') or row.get('posted_at') or 'recorded'}); nothing to do")
        return 0
    missing = [k for k in ENV if not os.environ.get(k)]
    if missing:
        log(f"skipping: missing {', '.join(missing)}")
        return 0
    creds = tuple(os.environ[k] for k in ENV)
    for url in URL_RE.findall(post):
        if not is_live(url):
            log(f"skipping: {url} is not live yet")
            return 0
    assert_brand_account(creds)

    image_path = None
    try:
        info = prepare_issue_image(meta)
        image_path = info.get("path")
        image_id = upload_image(creds, image_path)
        if has_video:
            _drop_temp(fetch_video(meta))
            log("newsreel checked. X allows one video or up to four images on a post, not both, "
                "so this post attaches the generated image. The issue page has the newsreel.")
        # One call, no reply: a thread is a rejected post, not a fallback.
        tid = create_post(creds, post, media_ids=[image_id])
    finally:
        _drop_temp(image_path)
    state[meta["id"]] = {"tweet_ids": [tid], "complete": True, "mode": "long",
                         "posted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                         "url": f"https://x.com/{ALLOWED_ACCOUNT}/status/{tid}",
                         "image_style": info.get("style_id"), "image_url": info.get("url")}
    save_state(a.state, state)
    log(f"done: https://x.com/{ALLOWED_ACCOUNT}/status/{tid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
