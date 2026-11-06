#!/usr/bin/env python3
"""Render a branded image for an X (@nordiccryptobot) post from a story or event.

Uses Cloudflare Workers AI (CF_AI_TOKEN + CF_ACCOUNT_ID, same as story_translate) to
generate a picture whose prompt is built from the item's English headline/summary and
a rotating visual style. «Nordic Crypto» (teal #1E3A45 / gold #D9A034) is always drawn
in the top-right corner afterwards. No outlet logos, no «Nordic Crypto AS», no
copyrighted comic characters.

Styles rotate and avoid the last few used (stored in the feed ledger under "styles").
Without CF credentials the script falls back to a Pillow headline card so the post
still gets a custom image instead of the generic site og:image.

  python3 tools/x_post_image.py --story-json '{"title_en":"…","summary":"…","country":"SE"}' -o out.png
  python3 tools/x_post_image.py --event-json '…' -o out.png [--styles-state state.json]
"""
from __future__ import annotations

import argparse, base64, io, json, os, random, re, sys, tempfile, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAL = (0x1E, 0x3A, 0x45)
GOLD = (0xD9, 0xA0, 0x34)
WHITE = (0xF0, 0xF1, 0xEC)
W, H = 1280, 720
MODEL = "@cf/black-forest-labs/flux-1-schnell"
RECENT = 4  # do not reuse a style from the last RECENT picks
FONT_SERIF = os.path.join(ROOT, "assets", "fonts", "CormorantGaramond-SemiBold.ttf")
FONT_SANS = os.path.join(ROOT, "assets", "fonts", "SchibstedGrotesk-Medium.ttf")
MARK = os.path.join(ROOT, "assets", "brand", "mark-64.png")

# id -> short prompt fragment. Never name Tintin, Snowy or other copyrighted characters.
STYLES = [
    ("photoreal-editorial",
     "photoreal editorial photography, sharp detail, natural Nordic light, magazine cover quality"),
    ("watercolour",
     "loose watercolour painting on textured paper, soft washes, visible brush edges"),
    ("flat-vector",
     "flat vector illustration, bold shapes, limited palette, clean edges, poster design"),
    ("isometric-3d",
     "isometric 3D illustration, soft studio lighting, clean geometric forms"),
    ("neon-cyberpunk",
     "neon cyberpunk night scene, teal and gold glow, rain-slick streets, futuristic Nordic city"),
    ("paper-collage",
     "hand-cut paper collage, layered coloured card stock, craft texture, studio photo of the collage"),
    ("ink-sketch",
     "black ink sketch with sparse gold wash accents, cross-hatching, notebook page feel"),
    ("retro-poster",
     "1960s travel poster, silk-screen print look, bold typography space left clear of text"),
    ("minimal-geometric",
     "minimal geometric composition, large flat colour fields, Bauhaus-inspired shapes"),
    ("cinematic-night",
     "cinematic night photography, deep teal shadows, warm gold highlights, shallow depth of field"),
    ("ligne-claire",
     "ligne claire Franco-Belgian comic illustration, clean black outlines, flat bright colours, "
     "even lighting, original adult characters only, never any copyrighted comic characters"),
]
STYLE_IDS = [s[0] for s in STYLES]
STYLE_PROMPT = {s[0]: s[1] for s in STYLES}

COUNTRY = {
    "NO": "Norway", "SE": "Sweden", "DK": "Denmark", "FI": "Finland", "IS": "Iceland",
    "FO": "the Faroe Islands", "GL": "Greenland", "AX": "Åland",
}

BANNED = re.compile(
    r"\b(tintin|snowy|milou|haddock|calculus|touriffon|herg[eé]|crypto\s*nordic|"
    r"nordic\s*crypto\s*as)\b",
    re.I,
)


def log(msg):
    print(f"[x-post-image] {msg}", file=sys.stderr, flush=True)


def _endpoint():
    account = os.environ.get("CF_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    token = os.environ.get("CF_AI_TOKEN") or os.environ.get("CLOUDFLARE_AI_TOKEN")
    return account, token


def pick_style(recent=None, rng=None):
    """Choose a style id that is not among the last RECENT used ones when possible."""
    recent = list(recent or [])
    banned = set(recent[-RECENT:])
    choices = [s for s in STYLE_IDS if s not in banned] or list(STYLE_IDS)
    rng = rng or random.Random()
    return rng.choice(choices)


def remember_style(recent, style_id, keep=12):
    out = list(recent or []) + [style_id]
    return out[-keep:]


def _plain(text, limit=280):
    text = " ".join(str(text or "").split())
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return text


def story_prompt(item, style_id):
    title = _plain(item.get("title_en") or item.get("title") or "Nordic crypto news", 160)
    summary = _plain(item.get("summary") or item.get("summary_en") or "", 220)
    country = COUNTRY.get((item.get("country") or "").upper(), "the Nordics")
    scene = summary or f"a scene that evokes the news: {title}"
    style = STYLE_PROMPT[style_id]
    prompt = (
        f"{style}. Wide 16:9 landscape. Subject inspired by this Nordic crypto news from {country}: "
        f"«{title}». Visual mood: {scene}. "
        f"No readable text, no logos, no watermarks, no newspaper mastheads, no brand marks, "
        f"no copyrighted comic characters. Leave the top-right corner visually quiet for a later overlay."
    )
    return BANNED.sub("figure", prompt)


def event_prompt(item, style_id):
    title = _plain(item.get("title") or "Nordic crypto event", 160)
    place = _plain(", ".join(x for x in (item.get("place"), item.get("city")) if x), 120)
    country = COUNTRY.get((item.get("country") or "").upper(), "the Nordics")
    where = place or ("online gathering" if item.get("online") else country)
    style = STYLE_PROMPT[style_id]
    prompt = (
        f"{style}. Wide 16:9 landscape. A welcoming gathering for the crypto event «{title}» "
        f"in {where}, {country}. People as original characters only. "
        f"No readable text, no logos, no watermarks, no copyrighted comic characters. "
        f"Leave the top-right corner visually quiet for a later overlay."
    )
    return BANNED.sub("figure", prompt)


def generate_ai(prompt, *, seed=None):
    """Call Workers AI flux-1-schnell. Returns JPEG/PNG bytes, or None on skip/failure."""
    account, token = _endpoint()
    if not account or not token:
        return None
    model = os.environ.get("CF_IMAGE_MODEL") or MODEL
    body = {"prompt": prompt[:2000], "steps": int(os.environ.get("CF_IMAGE_STEPS") or 4)}
    if seed is not None:
        body["seed"] = int(seed)
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "nordic-crypto-x-post-image/1 (+https://nordiccrypto.no/)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            res = json.load(r)
    except urllib.error.HTTPError as err:
        log(f"Workers AI HTTP {err.code}: {err.read()[:200].decode('utf-8', 'replace')}")
        return None
    except Exception as err:
        log(f"Workers AI failed: {type(err).__name__}: {err}")
        return None
    result = res.get("result") or {}
    b64 = result.get("image") if isinstance(result, dict) else None
    if not b64:
        log("Workers AI returned no image")
        return None
    return base64.b64decode(b64)


def _fit(im):
    """Cover-fit to W×H."""
    from PIL import Image
    im = im.convert("RGB")
    scale = max(W / im.width, H / im.height)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - W) // 2, (nh - H) // 2
    return im.crop((left, top, left + W, top + H))


def brand_overlay(im):
    """Draw «Nordic Crypto» (Nordic white, Crypto gold) in a teal pill at the top-right."""
    from PIL import Image, ImageDraw, ImageFont
    im = im.convert("RGBA")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype(FONT_SERIF, 42)
    except OSError:
        font = ImageFont.load_default()
    nordic, crypto = "Nordic ", "Crypto"
    tw = d.textlength(nordic, font=font) + d.textlength(crypto, font=font)
    pad_x, pad_y, gap = 22, 14, 12
    mark_h = 40
    try:
        mark = Image.open(MARK).convert("RGBA")
        r = mark_h / mark.height
        mark = mark.resize((max(1, round(mark.width * r)), mark_h), Image.LANCZOS)
    except Exception:
        mark = None
    mark_w = mark.width if mark else 0
    box_w = int(pad_x * 2 + (mark_w + gap if mark else 0) + tw)
    box_h = int(pad_y * 2 + max(mark_h, 48))
    x1, y1 = W - 28 - box_w, 24
    x2, y2 = x1 + box_w, y1 + box_h
    # rounded teal plate with thin gold edge
    d.rounded_rectangle([x1 - 1, y1 - 1, x2 + 1, y2 + 1], radius=14, fill=GOLD + (255,))
    d.rounded_rectangle([x1, y1, x2, y2], radius=13, fill=TEAL + (240,))
    tx = x1 + pad_x
    if mark:
        im.alpha_composite(mark, (tx, y1 + (box_h - mark_h) // 2))
        tx += mark_w + gap
    ty = y1 + box_h // 2
    d.text((tx, ty), nordic, font=font, fill=WHITE + (255,), anchor="lm")
    d.text((tx + d.textlength(nordic, font=font), ty), crypto, font=font, fill=GOLD + (255,), anchor="lm")
    return im.convert("RGB")


def fallback_card(headline, subtitle=""):
    """Pillow brand card when AI is unavailable: teal field, gold rule, headline."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 12, W, H], fill=GOLD)
    try:
        big = ImageFont.truetype(FONT_SERIF, 64)
        small = ImageFont.truetype(FONT_SANS, 28)
    except OSError:
        big = small = ImageFont.load_default()
    # wrap headline
    maxw, pad = W - 120, 60
    words, lines, cur = (headline or "Nordic Crypto").split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=big) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    lines = lines[:4]
    y = 160
    d.line([(pad, y), (pad + 120, y)], fill=GOLD, width=6)
    y += 36
    for ln in lines:
        d.text((pad, y), ln, font=big, fill=WHITE); y += 76
    if subtitle:
        d.text((pad, min(y + 20, H - 80)), _plain(subtitle, 90), font=small, fill=(0xD9, 0xE3, 0xE6))
    return im


def render(item, out_path, *, kind="news", recent_styles=None, rng=None, generator=None, style=None):
    """Write a branded PNG for item. Returns (style_id, path). generator(prompt)->bytes for tests."""
    recent = list(recent_styles or [])
    style_id = style if style in STYLE_PROMPT else pick_style(recent, rng=rng)
    prompt = story_prompt(item, style_id) if kind == "news" else event_prompt(item, style_id)
    raw = (generator or generate_ai)(prompt)
    from PIL import Image
    if raw:
        try:
            im = _fit(Image.open(io.BytesIO(raw)))
        except Exception as err:
            log(f"decode failed ({type(err).__name__}); using fallback card")
            raw = None
    if not raw:
        title = item.get("title_en") or item.get("title") or "Nordic Crypto"
        sub = item.get("source_name") or item.get("city") or ""
        # never put an outlet logo; source_name as plain subtitle is fine
        if kind == "news" and sub:
            sub = f"Source: {sub}"
        im = fallback_card(_plain(title, 120), sub)
        log(f"fallback card ({style_id})")
    else:
        log(f"generated {style_id}")
    im = brand_overlay(im)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    im.save(out_path, "PNG", optimize=True)
    return style_id, out_path


def load_styles(path):
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("styles") or [])


def save_styles(path, styles):
    """Merge styles into an existing ledger JSON without dropping other keys."""
    data = {}
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh) or {}
        except (OSError, json.JSONDecodeError):
            data = {}
    data["styles"] = list(styles)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--story-json", help="JSON object for a news item")
    g.add_argument("--event-json", help="JSON object for an event")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--styles-state", help="ledger JSON to read/write recent style ids")
    ap.add_argument("--style", choices=STYLE_IDS, help="force a style (skips rotation)")
    a = ap.parse_args(argv)
    kind = "news" if a.story_json is not None else "events"
    item = json.loads(a.story_json if kind == "news" else a.event_json)
    recent = load_styles(a.styles_state)
    style_id, path = render(item, a.out, kind=kind, recent_styles=recent, style=a.style)
    if a.styles_state:
        save_styles(a.styles_state, remember_style(recent, style_id))
    print(path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:
        log(f"fatal: {type(err).__name__}: {err}")
        sys.exit(1)
