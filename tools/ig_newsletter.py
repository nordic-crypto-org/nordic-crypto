#!/usr/bin/env python3
"""Post each new Nordic Crypto newsletter issue to Instagram as one Reel, once, with a branded cover.

Without cover_url Instagram uses frame 0, and the newsreels open on black. The cover is the issue's
thumbnail-vertical.png (1080x1920) on nordiccrypto.no; if it is not live, thumb_offset skips the fade-in.
The video is the -vertical.mp4 cut beside video.url when it exists, else video.url.

State: data/ig_posted.json (issue id -> media id). Secrets (env, never printed): IG_USER_ID, FB_PAGE_ACCESS_TOKEN.

  python3 tools/ig_newsletter.py [--issue 003] [--dry-run] [--state data/ig_posted.json]
"""
import argparse, datetime as dt, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fb_newsletter import ROOT, SITE, issue_url, is_live, load_issue, load_state, save_state
from youtube_meta import LOGOS, NFA

STATE = os.path.join(ROOT, "data", "ig_posted.json")
GRAPH = "https://graph.facebook.com/v23.0"
ENV = ("IG_USER_ID", "FB_PAGE_ACCESS_TOKEN")
THUMB_OFFSET_MS = 2000


def log(msg):
    print(f"[ig-newsletter] {msg}", file=sys.stderr, flush=True)


def build_post(meta):
    n = meta.get("number") or int(meta["id"])
    title = f"Nordic Crypto #{n}: " + re.sub(rf"^Nordic Crypto #{n}:\s*", "", meta["title"])
    caption = "\n\n".join([title, meta.get("subtitle", ""), f"Read the issue and all sources: {issue_url(meta)}", LOGOS, NFA])
    return {"caption": caption[:2200]}


def cover_url(meta):
    return f"{SITE}/newsletter/{meta['id']}/thumbnail-vertical.png"


def video_url(meta, live=is_live):
    url = (meta.get("video") or {}).get("url")
    if not url:
        return None
    vert = re.sub(r"\.mp4$", "-vertical.mp4", url)
    return vert if vert != url and live(vert) else url


def graph(method, path, fields):
    data = urllib.parse.urlencode(fields).encode()
    url = f"{GRAPH}/{path}"
    req = urllib.request.Request(url, data=data, method="POST") if method == "POST" else urllib.request.Request(f"{url}?{data.decode()}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Graph API -> {e.code}: {e.read()[:500].decode('utf-8', 'replace')}")


def media_fields(meta, video, cover_live):
    f = {"media_type": "REELS", "video_url": video, "caption": build_post(meta)["caption"], "share_to_feed": "true"}
    if cover_live:
        f["cover_url"] = cover_url(meta)
    else:
        f["thumb_offset"] = str(THUMB_OFFSET_MS)
    return f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--issue")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--state", default=STATE)
    a = ap.parse_args(argv)

    meta = load_issue(a.issue)
    state = load_state(a.state)
    if a.dry_run:
        f = media_fields(meta, video_url(meta) or "-", is_live(cover_url(meta)))
        print(f"# Issue {meta['id']}: Instagram Reel{' [already posted]' if meta['id'] in state else ''}")
        for k, v in f.items():
            print(f"{k}: {v}")
        return 0
    if meta["id"] in state:
        log(f"issue {meta['id']} already posted; nothing to do")
        return 0
    missing = [k for k in ENV if not os.environ.get(k)]
    if missing:
        log(f"skipping: missing {', '.join(missing)}")
        return 0
    video = video_url(meta)
    if not video or not is_live(issue_url(meta)):
        log(f"skipping: issue {meta['id']} has no video or its page is not live yet")
        return 0
    ig, token = os.environ["IG_USER_ID"], os.environ["FB_PAGE_ACCESS_TOKEN"]
    fields = media_fields(meta, video, is_live(cover_url(meta)))
    log("cover: " + fields.get("cover_url", f"thumb_offset {THUMB_OFFSET_MS} ms"))
    cid = graph("POST", f"{ig}/media", dict(fields, access_token=token))["id"]
    for _ in range(60):
        st = graph("GET", cid, {"fields": "status_code", "access_token": token}).get("status_code")
        if st in ("FINISHED", "ERROR", "EXPIRED"):
            break
        time.sleep(10)
    if st != "FINISHED":
        raise RuntimeError(f"container {cid}: {st}")
    mid = graph("POST", f"{ig}/media_publish", {"creation_id": cid, "access_token": token})["id"]
    link = graph("GET", mid, {"fields": "permalink", "access_token": token}).get("permalink")
    state[meta["id"]] = {"media_id": mid, "permalink": link, "posted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    save_state(a.state, state)
    log(f"done: {link}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
