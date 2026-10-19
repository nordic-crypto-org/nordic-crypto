#!/usr/bin/env python3
"""Rule checks for build/youtube/<id>/ before anything is uploaded.

  python3 tools/youtube_lint.py build/youtube [--report lint.json]
Prints one line per video; exits 1 if any video fails. Failing videos are never uploaded.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtube_meta import LOGOS, NFA

EMAIL = "jqrgen@nordiccrypto.no"
BANNED = re.compile(r"\b(buy|sell|price targets?|free nfts?|giveaways?|airdrops?|made with ai|ai[- ]generated"
                    r"|crypto nordic|crypto shield|nexa)\b", re.I)
PHONE = re.compile(r"(?<![\w/=.-])(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){8,11}\d?(?![\w/])")
NON_EN = re.compile(r"\b(nettside|les mer|kilde|nyhetsbrev|utgave|läs|källa|lue lisää)\b|nordiccrypto\.no/(nb|nn|sv|da|fi|is)/", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL_RE = re.compile(r"https?://\S+")


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True, check=True)
    d = json.loads(out.stdout)
    return d["streams"][0]["width"], d["streams"][0]["height"], float(d["format"]["duration"])


def check(meta, folder=None):
    err = []
    text = f"{meta.get('title', '')}\n{meta.get('description', '')}\n{' '.join(meta.get('tags', []))}"
    bare = URL_RE.sub(" ", text)
    if "Nordic Crypto" not in meta.get("title", "") + meta.get("description", ""):
        err.append("brand «Nordic Crypto» missing")
    if NFA not in meta.get("description", ""):
        err.append("missing «Not financial advice» line")
    if LOGOS not in meta.get("description", ""):
        err.append("missing logos disclaimer")
    if "#shorts" in meta.get("title", "").lower():
        err.append("#Shorts in title")
    if len(re.findall(r"#\w+", meta.get("description", ""))) > 5:
        err.append("more than 5 hashtags")
    if meta.get("defaultLanguage") != "en" or meta.get("defaultAudioLanguage") != "en" or NON_EN.search(text):
        err.append("metadata not English")
    if PHONE.search(bare):
        err.append("phone-number pattern")
    if any(e.lower() != EMAIL for e in EMAIL_RE.findall(bare)):
        err.append("email other than " + EMAIL)
    if m := BANNED.search(text):
        err.append(f"banned term: {m.group(0)}")
    if meta.get("tts", True) and meta.get("containsSyntheticMedia") is not True:
        err.append("TTS without containsSyntheticMedia")
    if meta.get("thumbnail_logos"):
        err.append("logo in thumbnail/title card")
    if folder:
        video = os.path.join(folder, meta.get("video") or "video.mp4")
        if not os.path.exists(video):
            err.append("video file missing")
        else:
            w, h, dur = probe(video)
            if meta.get("short") and ((w, h) != (1080, 1920) or dur > 60):
                err.append(f"Short must be 1080x1920 and ≤60 s (got {w}x{h}, {dur:.0f} s)")
            if not meta.get("short") and (w, h) != (1920, 1080):
                err.append(f"long-form must be 1920x1080 (got {w}x{h})")
    return err


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "build/youtube"
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    results = {}
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        folder = os.path.join(root, name)
        if os.path.isfile(os.path.join(folder, "meta.json")):
            results[name] = check(json.load(open(os.path.join(folder, "meta.json"), encoding="utf-8")), folder)
    for name, err in results.items():
        print(f"{'FAIL' if err else 'ok  '} {name}" + (": " + "; ".join(err) if err else ""))
    if report:
        json.dump(results, open(report, "w"), indent=1)
    sys.exit(1 if any(results.values()) else 0)


if __name__ == "__main__":
    main()
