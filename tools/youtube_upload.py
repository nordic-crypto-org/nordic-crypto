#!/usr/bin/env python3
"""Upload a newsletter newsreel to YouTube once per issue (Data API v3, resumable videos.insert).

  tools/youtube_upload.py --issue 003 FILE [--title T] [--description D] [--thumbnail PNG] [--record] [--dry-run]

Skips (exit 0, prints the existing URL) when the issue already has a video:
  1. video.youtube is set for the issue in newsletter/published/issues.json, or
  2. the channel's uploads already hold a video titled «Nordic Crypto #<n>:…».
An exclusive file lock (YT_UPLOAD_LOCK, default /tmp/nordic-crypto-youtube-upload.lock) stops two
runs on one machine; the workflow's concurrency group does the same on GitHub Actions.
--force skips the checks (not the lock). --record writes the new URL into issues.json.
Auth: YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN (or --token-file JSON with refresh_token).
Never prints secrets."""
import argparse, fcntl, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ISSUES = Path(__file__).resolve().parent.parent / "newsletter" / "published" / "issues.json"
API = "https://www.googleapis.com/youtube/v3/"


def access_token(token_file):
    rt = os.environ.get("YT_REFRESH_TOKEN") or json.load(open(os.path.expanduser(token_file)))["refresh_token"]
    data = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": rt,
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"]}).encode()
    try:
        return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", data, timeout=60))["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"token refresh failed: HTTP {e.code}")


def get(at, path):
    r = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + at})
    return json.load(urllib.request.urlopen(r, timeout=60))


def find_issue(doc, issue):
    for it in doc["issues"]:
        if it["id"] == issue:
            return it
    sys.exit(f"issue {issue} not in {ISSUES}")


def on_channel(at, number):
    """Return the watch URL of an upload titled «Nordic Crypto #<number>:…», else None."""
    prefix = f"Nordic Crypto #{number}:"
    ch = get(at, "channels?part=contentDetails&mine=true")["items"][0]
    pl, page = ch["contentDetails"]["relatedPlaylists"]["uploads"], ""
    for _ in range(4):  # newest 200 uploads is plenty for a weekly issue
        r = get(at, f"playlistItems?part=snippet&maxResults=50&playlistId={pl}" + (f"&pageToken={page}" if page else ""))
        for i in r["items"]:
            if i["snippet"]["title"].startswith(prefix):
                return "https://www.youtube.com/watch?v=" + i["snippet"]["resourceId"]["videoId"]
        page = r.get("nextPageToken")
        if not page:
            return None
    return None


def upload(at, a, title):
    meta = {"snippet": {"title": title[:100], "description": a.description, "categoryId": a.category},
            "status": {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False}}
    req = urllib.request.Request(API.replace("/youtube/", "/upload/youtube/") + "videos?uploadType=resumable&part=snippet,status",
        json.dumps(meta).encode(), {"Authorization": "Bearer " + at, "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/*", "X-Upload-Content-Length": str(os.path.getsize(a.file))}, method="POST")
    loc = urllib.request.urlopen(req, timeout=60).headers["Location"]
    for attempt in range(5):
        try:
            with open(a.file, "rb") as f:
                r = urllib.request.Request(loc, f.read(), {"Authorization": "Bearer " + at, "Content-Type": "video/*"}, method="PUT")
                vid = json.load(urllib.request.urlopen(r, timeout=1800))["id"]
            break
        except urllib.error.HTTPError as e:
            if e.code < 500:
                sys.exit(f"upload failed: HTTP {e.code} {e.read()[:300].decode(errors='replace')}")
        except OSError:
            pass
        time.sleep(2 ** attempt * 5)
    else:
        sys.exit("upload failed after retries")
    if a.thumbnail:
        ct = "image/png" if a.thumbnail.endswith(".png") else "image/jpeg"
        try:
            urllib.request.urlopen(urllib.request.Request(API.replace("/youtube/", "/upload/youtube/") + "thumbnails/set?videoId=" + vid,
                open(a.thumbnail, "rb").read(), {"Authorization": "Bearer " + at, "Content-Type": ct}, method="POST"), timeout=120)
        except urllib.error.HTTPError as e:
            print(f"thumbnail failed: HTTP {e.code}", file=sys.stderr)
    return "https://www.youtube.com/watch?v=" + vid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file"); ap.add_argument("--issue", required=True, help="issue id, e.g. 003")
    ap.add_argument("--title"); ap.add_argument("--description", default="")
    ap.add_argument("--privacy", default="public"); ap.add_argument("--category", default="25")
    ap.add_argument("--thumbnail"); ap.add_argument("--token-file", default="~/.youtube_token_nordiccryptotv.json")
    ap.add_argument("--record", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    lock = open(os.environ.get("YT_UPLOAD_LOCK", "/tmp/nordic-crypto-youtube-upload.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("another YouTube upload is running; not starting a second one")

    doc = json.loads(ISSUES.read_text())
    it = find_issue(doc, a.issue)
    title = a.title or it["title"]
    if not re.match(rf"Nordic Crypto #{it['number']}:", title):
        sys.exit(f"title must start with «Nordic Crypto #{it['number']}:»")
    if not a.force and (it.get("video") or {}).get("youtube"):
        print(f"skip: issue {a.issue} already has {it['video']['youtube']} in issues.json"); return
    at = access_token(a.token_file)
    if not a.force:
        url = on_channel(at, it["number"])
        if url:
            print(f"skip: the channel already has #{it['number']} at {url}"); return
    if a.dry_run:
        print(f"dry run: would upload {a.file} as «{title[:100]}»"); return
    url = upload(at, a, title)
    print(url)
    if a.record:
        # Insert one line instead of re-dumping, so the hand-formatted file keeps its layout.
        text, old = ISSUES.read_text(), (it.get("video") or {}).get("youtube")
        start = text.index(f'"id": "{a.issue}"')
        if old:  # --force re-upload: swap the stored URL
            ISSUES.write_text(text[:start] + text[start:].replace(old, url, 1)); return
        at_video = text.index('"video": {', start) + len('"video": {')
        ISSUES.write_text(text[:at_video] + f'\n    "youtube": "{url}",' + text[at_video:])
        json.loads(ISSUES.read_text())  # still valid JSON


if __name__ == "__main__":
    main()
