#!/usr/bin/env python3
"""Publish the due TikTok post via the Content Posting API (Direct Post, scope video.publish).
  tools/tiktok_post.py [--dry-run] [--now ISO] [--state FILE] [--rotated FILE]
Due = when_utc <= now <= when_utc + 3 h, not in the state file and not "pending".
Without TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / TIKTOK_REFRESH_TOKEN it exits 0 and posts nothing.
Posts only PUBLIC_TO_EVERYONE; if the app is unaudited (SELF_ONLY only) it stops without posting.
A rotated refresh token is written to --rotated (never printed). Never prints secrets."""
import argparse, datetime as dt, json, os, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://open.tiktokapis.com/v2/"
SHIELD = ("shield",)


def posts():
    return [json.loads(p.read_text()) for p in sorted((ROOT / "tiktok" / "posts").glob("*/post.json"))]


def due(now, done):
    for m in posts():
        t = dt.datetime.fromisoformat(m["when_utc"].replace("Z", "+00:00"))
        if m["id"] not in done and m["kind"] != "pending" and t <= now <= t + dt.timedelta(hours=3):
            return m
    return None


def check(m):
    text = (m.get("caption", "") + json.dumps(m.get("cards", []))).lower()
    assert not any(w in text for w in SHIELD), "Shield content is not allowed on TikTok"
    assert "Not financial advice." in m["caption"], "caption must carry the disclaimer"


def call(url, body=None, token=None, form=False, method="POST", headers=None):
    h = dict(headers or {})
    if token: h["Authorization"] = f"Bearer {token}"
    if form:
        data = urllib.parse.urlencode(body).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
    elif isinstance(body, bytes):
        data = body
    else:
        data = json.dumps(body or {}).encode(); h["Content-Type"] = "application/json; charset=UTF-8"
    with urllib.request.urlopen(urllib.request.Request(url, data, h, method=method), timeout=120) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def ok(r, what):
    err = (r.get("error") or {})
    if err.get("code") not in (None, "ok"):
        sys.exit(f"{what}: {err.get('code')} {err.get('message', '')}")
    return r.get("data", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--now")
    ap.add_argument("--state", default=str(ROOT / "build" / "tiktok_posted.json"))
    ap.add_argument("--rotated", default="")
    a = ap.parse_args()
    now = dt.datetime.fromisoformat(a.now.replace("Z", "+00:00")) if a.now else dt.datetime.now(dt.timezone.utc)
    state = Path(a.state); done = json.loads(state.read_text()) if state.exists() else {}
    m = due(now, done)
    if not m:
        print("nothing due"); return
    check(m)
    print(f"due: {m['id']} ({m['when_utc']}) aigc={m['aigc']} brand_organic={m['brand_organic']}")
    if subprocess.run([sys.executable, str(ROOT / "tools" / "tiktok_render.py"), m["id"]]).returncode:
        sys.exit("render failed")
    video = ROOT / "build" / "tiktok" / f"{m['id']}.mp4"
    keys = [os.environ.get(k, "") for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN")]
    if not all(keys):
        print("TikTok secrets not set: skipped, nothing posted"); return
    if a.dry_run:
        print("dry run: nothing posted"); return
    tok = call(API + "oauth/token/", {"client_key": keys[0], "client_secret": keys[1], "grant_type": "refresh_token",
                                       "refresh_token": keys[2]}, form=True)
    if "access_token" not in tok:
        sys.exit(f"token refresh failed: {tok.get('error', 'unknown')}")
    access = tok["access_token"]; print(f"::add-mask::{access}")
    new_rt = tok.get("refresh_token")
    if new_rt and new_rt != keys[2] and a.rotated:
        print(f"::add-mask::{new_rt}")
        fd = os.open(a.rotated, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600); os.write(fd, new_rt.encode()); os.close(fd)
    info = ok(call(API + "post/publish/creator_info/query/", {}, access), "creator_info")
    if "PUBLIC_TO_EVERYONE" not in info.get("privacy_level_options", []):
        sys.exit(f"public posting not allowed (options: {info.get('privacy_level_options')}); app not audited? nothing posted")
    size = video.stat().st_size
    init = ok(call(API + "post/publish/video/init/", {
        "post_info": {"title": m["caption"], "privacy_level": "PUBLIC_TO_EVERYONE", "disable_comment": False,
                      "disable_duet": False, "disable_stitch": False, "is_aigc": bool(m["aigc"]),
                      "brand_organic_toggle": bool(m["brand_organic"]), "brand_content_toggle": False},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}}, access), "init")
    call(init["upload_url"], video.read_bytes(), method="PUT",
         headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size - 1}/{size}"})
    for _ in range(60):
        st = ok(call(API + "post/publish/status/fetch/", {"publish_id": init["publish_id"]}, access), "status")
        if st.get("status") == "PUBLISH_COMPLETE": break
        if st.get("status") == "FAILED": sys.exit(f"publish failed: {st.get('fail_reason')}")
        time.sleep(10)
    done[m["id"]] = {"publish_id": init["publish_id"], "at": now.isoformat(timespec="seconds"), "status": st.get("status")}
    state.parent.mkdir(parents=True, exist_ok=True); state.write_text(json.dumps(done, indent=1) + "\n")
    print(f"posted {m['id']}: {st.get('status')}")


if __name__ == "__main__":
    main()
