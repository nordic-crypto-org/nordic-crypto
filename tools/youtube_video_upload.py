#!/usr/bin/env python3
"""Upload checked jobs from build/youtube/<id>/ to @NordicCryptoTV (YouTube Data API v3).

  python3 tools/youtube_video_upload.py build/youtube [--dry-run]
Each video goes in as private with publishAt (YouTube makes it public at that time), containsSyntheticMedia,
English languages, category 25, not made for kids. Then thumbnail (long-form only), captions, playlists.
Re-runs the rule checks: a failing job is skipped and reported. data/youtube_posted.json records every upload;
a recorded id is never uploaded again. Auth: env YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN. Never prints secrets.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import youtube_lint

POSTED = os.path.join(ROOT, "data", "youtube_posted.json")
API = "https://www.googleapis.com/youtube/v3/"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/"


def token():
    data = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": os.environ["YT_REFRESH_TOKEN"],
                                   "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"]}).encode()
    try:
        return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", data, timeout=60))["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"token refresh failed: HTTP {e.code} {json.loads(e.read() or b'{}').get('error')}")


def call(at, url, body=None, ctype="application/json", method="POST", headers=None):
    if isinstance(body, dict):
        body = json.dumps(body).encode()
    r = urllib.request.Request(url, body, {"Authorization": "Bearer " + at, "Content-Type": ctype, **(headers or {})}, method=method)
    with urllib.request.urlopen(r, timeout=1800) as resp:
        return resp.headers, resp.read()


def resource(meta):
    return {
        "snippet": {k: meta[k] for k in ("title", "description", "tags", "categoryId", "defaultLanguage", "defaultAudioLanguage")},
        "status": {"privacyStatus": "private", "publishAt": meta["publishAt"], "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(meta["containsSyntheticMedia"]), "embeddable": True, "license": "youtube"},
    }


def upload(at, folder, meta):
    path = os.path.join(folder, meta["video"])
    hdr, _ = call(at, UPLOAD + "videos?uploadType=resumable&part=snippet,status", resource(meta),
                  "application/json; charset=UTF-8",
                  headers={"X-Upload-Content-Type": "video/*", "X-Upload-Content-Length": str(os.path.getsize(path))})
    loc = hdr["Location"]
    for attempt in range(5):
        try:
            with open(path, "rb") as f:
                _, body = call(at, loc, f.read(), "video/*", "PUT")
            return json.loads(body)["id"]
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
        except OSError:
            pass
        time.sleep(2 ** attempt * 5)
    raise RuntimeError("upload failed after retries")


def extras(at, folder, meta, vid):
    notes = []
    steps = []
    if meta.get("thumbnail") and not meta.get("short"):
        steps.append(("thumbnail", lambda: call(at, UPLOAD + "thumbnails/set?videoId=" + vid,
                                                open(os.path.join(folder, meta["thumbnail"]), "rb").read(), "image/png")))
    if meta.get("captions") and os.path.exists(os.path.join(folder, meta["captions"])):
        b = "nc-caption-boundary"
        snippet = json.dumps({"snippet": {"videoId": vid, "language": "en", "name": "English"}})
        body = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{snippet}\r\n"
                f"--{b}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + \
            open(os.path.join(folder, meta["captions"]), "rb").read() + f"\r\n--{b}--".encode()
        steps.append(("captions", lambda: call(at, UPLOAD + "captions?uploadType=multipart&part=snippet", body,
                                               f"multipart/related; boundary={b}")))
    for pl in meta.get("playlists") or []:
        steps.append((f"playlist {pl}", lambda pl=pl: call(at, API + "playlistItems?part=snippet",
                      {"snippet": {"playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": vid}}})))
    for name, fn in steps:
        try:
            fn()
        except urllib.error.HTTPError as e:
            notes.append(f"{name} failed: HTTP {e.code}")
    return notes


def main():
    root = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else os.path.join(ROOT, "build", "youtube")
    dry = "--dry-run" in sys.argv
    posted = json.load(open(POSTED)) if os.path.exists(POSTED) else {}
    jobs = sorted(n for n in os.listdir(root) if os.path.isfile(os.path.join(root, n, "meta.json"))) if os.path.isdir(root) else []
    at, failed = None, []
    for name in jobs:
        folder = os.path.join(root, name)
        meta = json.load(open(os.path.join(folder, "meta.json"), encoding="utf-8"))
        if meta["id"] in posted:
            print(f"skip {meta['id']}: already uploaded as {posted[meta['id']]['video_id']}")
            continue
        err = youtube_lint.check(meta, folder)
        if err:
            failed.append(meta["id"])
            print(f"NOT UPLOADED {meta['id']}: " + "; ".join(err))
            continue
        if dry:
            print(f"dry run {meta['id']}: {meta['title']} (private, public at {meta['publishAt']})")
            continue
        at = at or token()
        try:
            vid = upload(at, folder, meta)
        except (urllib.error.HTTPError, RuntimeError) as e:
            failed.append(meta["id"])
            print(f"upload failed {meta['id']}: {getattr(e, 'code', e)}")
            continue
        notes = extras(at, folder, meta, vid)
        posted[meta["id"]] = {"video_id": vid, "posted_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "publish_at": meta["publishAt"]}
        json.dump(posted, open(POSTED, "w"), indent=1)
        print(f"uploaded {meta['id']}: https://www.youtube.com/watch?v={vid} (public at {meta['publishAt']})"
              + ("; " + "; ".join(notes) if notes else ""))
        if meta.get("issue"):
            set_issue_link(meta["issue"], vid)
    sys.exit(1 if failed else 0)


def set_issue_link(issue_id, vid):
    p = os.path.join(ROOT, "newsletter", "published", "issues.json")
    doc = json.load(open(p, encoding="utf-8"))
    for iss in doc["issues"]:
        if iss["id"] == issue_id and "video" in iss:
            iss["video"]["youtube"] = f"https://www.youtube.com/watch?v={vid}"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
