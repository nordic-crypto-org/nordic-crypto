#!/usr/bin/env python3
"""Prepare YouTube jobs in build/youtube/<id>/ {video.mp4, thumb.png, subs.srt, meta.json}. No YouTube access.

  python3 tools/youtube_render.py weekly [--issue 003]
weekly: the newest published newsletter newsreel (release asset, sha256-checked), skipped when already on YouTube.
Other series render into the same layout from their own pipelines.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import youtube_meta

OUT = os.path.join(ROOT, "build", "youtube")
POSTED = os.path.join(ROOT, "data", "youtube_posted.json")


def vtt_to_srt(vtt):
    blocks = [b for b in re.split(r"\n\s*\n", vtt.replace("\r", "").strip()) if "-->" in b]
    out = []
    for i, b in enumerate(blocks, 1):
        lines = b.split("\n")
        k = next(j for j, l in enumerate(lines) if "-->" in l)
        ts = re.sub(r"(\d\d:\d\d)\.(\d{3})", r"\1,\2", lines[k].split(" line:")[0].split(" align:")[0])
        ts = re.sub(r"(?<![\d:])(\d\d:\d\d,\d{3})", r"00:\1", ts)
        out.append(f"{i}\n{ts}\n" + "\n".join(lines[k + 1:]))
    return "\n\n".join(out) + "\n"


def weekly(issue_id=None):
    issues = json.load(open(os.path.join(ROOT, "newsletter", "published", "issues.json"), encoding="utf-8"))["issues"]
    iss = next(i for i in issues if i["id"] == issue_id) if issue_id else issues[0]
    jid = f"weekly-{iss['id']}"
    posted = json.load(open(POSTED)) if os.path.exists(POSTED) else {}
    if jid in posted or iss.get("video", {}).get("youtube"):
        print(f"{jid}: already on YouTube, nothing to render")
        return
    v = iss["video"]
    folder = os.path.join(OUT, jid)
    os.makedirs(folder, exist_ok=True)
    mp4 = os.path.join(folder, "video.mp4")
    urllib.request.urlretrieve(v["url"], mp4)
    h = hashlib.sha256()
    with open(mp4, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    if h.hexdigest() != v["sha256"]:
        sys.exit(f"{jid}: sha256 mismatch")
    src = os.path.join(ROOT, "newsletter", "published", iss["id"])
    shutil.copy(os.path.join(src, v.get("poster", "thumbnail.png")), os.path.join(folder, "thumb.png"))
    captions = None
    if os.path.exists(os.path.join(src, v.get("subs", "subs.vtt"))):
        open(os.path.join(folder, "subs.srt"), "w").write(vtt_to_srt(open(os.path.join(src, v.get("subs", "subs.vtt"))).read()))
        captions = "subs.srt"
    headline = iss["title"].split(": ", 1)[-1]
    meta = youtube_meta.build("weekly", id=jid, issue=iss["id"], number=iss["number"], headline=headline,
                              summary=iss["subtitle"], read_more=f"https://nordiccrypto.no/newsletter/{iss['id']}/",
                              day=dt.date.fromisoformat(iss["date"]), hashtags=("#NordicCrypto", "#Bitcoin", "#Crypto"))
    meta["captions"] = captions
    json.dump(meta, open(os.path.join(folder, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{jid}: {meta['title']} (publish {meta['publishAt']})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["weekly"])
    ap.add_argument("--issue")
    a = ap.parse_args()
    weekly(a.issue)
