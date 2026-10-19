#!/usr/bin/env python3
"""Render a TikTok post (tiktok/posts/<id>/post.json) to build/tiktok/<id>.mp4 (1080x1920, 30 fps, H.264).
  tools/tiktok_render.py <id>
kind "cards": brand title cards; kind "cut": keep listed ranges of a source video; kind "pending": not ready, exit 3."""
import json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TEAL, GOLD, IVORY = (14, 74, 82), (201, 162, 39), (246, 241, 230)
FONTS = ROOT / "assets" / "fonts"
W, H, X, COL = 1080, 1920, 140, 630  # text column x 140-770 (TikTok safe zone)
FOOT = "News and information only. Not financial advice."


def load(pid):
    return json.loads((ROOT / "tiktok" / "posts" / pid / "post.json").read_text())


def wrap(d, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur] if cur else lines


def card(label, text, last):
    im = Image.new("RGB", (W, H), TEAL); d = ImageDraw.Draw(im)
    d.rectangle([60, 60, W - 60, H - 60], outline=GOLD, width=4)
    mark = Image.open(ROOT / "assets" / "brand" / "mark-180.png").convert("RGBA").resize((96, 96))
    im.paste(mark, (X, 260), mark)
    small = ImageFont.truetype(str(FONTS / "SchibstedGrotesk-Medium.ttf"), 34)
    if label:
        d.text((X + 120, 290), label, font=small, fill=GOLD)
    size = 110 if len(text) < 30 else 72
    big = ImageFont.truetype(str(FONTS / "CormorantGaramond-SemiBold.ttf"), size)
    y = 440
    for ln in wrap(d, text, big, COL):
        d.text((X, y), ln, font=big, fill=GOLD if last else IVORY); y += int(size * 1.15)
    if last:
        d.text((X, 1210), FOOT, font=ImageFont.truetype(str(FONTS / "SchibstedGrotesk-Regular.ttf"), 26), fill=IVORY)
    return im


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def render(m, out):
    if m["kind"] == "cards":
        with tempfile.TemporaryDirectory() as t:
            parts = []
            for i, (label, text, secs) in enumerate(m["cards"]):
                png = Path(t) / f"{i}.png"; card(label, text, i == len(m["cards"]) - 1).save(png)
                mp4 = Path(t) / f"{i}.mp4"; parts.append(mp4)
                ff("-loop", "1", "-t", str(secs), "-i", str(png), "-vf", f"fade=in:d=0.3,fade=out:st={secs - 0.3}:d=0.3,format=yuv420p",
                   "-r", "30", "-c:v", "libx264", "-crf", "18", str(mp4))
            lst = Path(t) / "l.txt"; lst.write_text("".join(f"file '{p}'\n" for p in parts))
            ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out))
    elif m["kind"] == "cut":
        src, keep = ROOT / m["source"], m["keep"]
        chains = "".join(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];" for i, (a, b) in enumerate(keep))
        chains += "".join(f"[v{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=0,format=yuv420p[v]"
        ff("-i", str(src), "-filter_complex", chains, "-map", "[v]", "-an", "-r", "30", "-c:v", "libx264", "-crf", "18",
           "-movflags", "+faststart", str(out))
    else:
        raise ValueError(m["kind"])


def main():
    m = load(sys.argv[1])
    if m["kind"] == "pending":
        print(f"{m['id']}: not ready (pending), skipped"); sys.exit(3)
    out = ROOT / "build" / "tiktok" / f"{m['id']}.mp4"; out.parent.mkdir(parents=True, exist_ok=True)
    render(m, out); print(out)


if __name__ == "__main__":
    main()
