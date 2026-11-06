#!/usr/bin/env python3
"""The story illustration for an Anders Fjell newsreel segment.

The renderer asks the public API for the story. When that story has an image
URL, the PNG is downloaded once into the issue build directory (gitignored)
and used as the on-screen picture. No second generation. No outlet logo on
that segment. When the story has no image, the caller keeps its current art.
"""
from __future__ import annotations

import json, os, urllib.request

API = "https://nordiccrypto.no"
UA = "nordic-crypto-newsreel/1 (+https://nordiccrypto.no/)"


def cover(im, width, height):
    """Scale and centre-crop im to width x height."""
    im = im.convert("RGB")
    scale = max(width / im.width, height / im.height)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    im = im.resize((nw, nh))
    left, top = (nw - width) // 2, (nh - height) // 2
    return im.crop((left, top, left + width, top + height))


def image_url_from_story(payload):
    image = (payload or {}).get("image") if isinstance(payload, dict) else None
    if not isinstance(image, dict):
        return None
    url = image.get("url") or ""
    if str(url).startswith("https://"):
        return str(url)
    return None


def _read(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def cached_path(news_id, cache_dir, *, api_base=None, read=None, story=None):
    """Local PNG for news_id, or None. Downloads at most once into cache_dir."""
    if not news_id:
        return None
    os.makedirs(cache_dir, exist_ok=True)
    dest = os.path.join(cache_dir, f"{news_id}.png")
    if os.path.isfile(dest) and os.path.getsize(dest) > 32:
        return dest
    read = read or _read
    try:
        if story is None:
            base = (api_base or API).rstrip("/")
            raw = read(f"{base}/api/v1/news/{news_id}.json")
            story = json.loads(raw.decode("utf-8"))
        url = image_url_from_story(story)
        if not url:
            return None
        data = read(url)
    except Exception:
        return None
    if not data or len(data) < 32:
        return None
    tmp = dest + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest)
    return dest
