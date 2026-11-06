#!/usr/bin/env python3
"""Draw a 1280x720 illustration for one Nordic Crypto story.

Cloudflare Workers AI flux-1-schnell (CF_AI_TOKEN + CF_ACCOUNT_ID, the same
names story translation uses) paints the picture. «Nordic Crypto» is drawn
afterwards in the top-right corner. Without those credentials the picture is
a Pillow headline card, so a post and a page still have an image of their own.

The style library and the recent-style list live in D1 (tools/story_images.py),
not in this file and not in git. This module only picks and paints.

No outlet logos. Ligne claire is allowed only with original characters.
No copyrighted comic cast.

  python3 tools/x_post_image.py --story-json '{"title_en":"…","summary":"…"}' -o out.png
"""
from __future__ import annotations

import argparse, base64, io, json, os, random, re, sys, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAL = (0x1E, 0x3A, 0x45)
GOLD = (0xD9, 0xA0, 0x34)
WHITE = (0xF0, 0xF1, 0xEC)
W, H = 1280, 720
MODEL = "@cf/black-forest-labs/flux-1-schnell"
# A style in this window is not used again. When every style is inside the
# window, the caller mints a new topic style instead of repeating one.
RECENT_LIMIT = 48
FONT_SERIF = os.path.join(ROOT, "assets", "fonts", "CormorantGaramond-SemiBold.ttf")
FONT_SANS = os.path.join(ROOT, "assets", "fonts", "SchibstedGrotesk-Medium.ttf")
MARK = os.path.join(ROOT, "assets", "brand", "mark-64.png")

COUNTRY = {
    "NO": "Norway", "SE": "Sweden", "DK": "Denmark", "FI": "Finland", "IS": "Iceland",
    "FO": "the Faroe Islands", "GL": "Greenland", "AX": "Åland",
}

# Names of copyrighted characters, and the legal-entity form we do not print.
BANNED = re.compile(
    r"\b(tintin|snowy|milou|haddock|calculus|tournesol|herg[eé]|"
    r"nordic\s*crypto\s*as)\b",
    re.I,
)
# Outlet names that must not be sent to the model as something to draw.
OUTLETS = re.compile(
    r"\b(NRK|E24|SVT|TV\s*2|Aftenposten|VG|Dagbladet|Dagens\s*Næringsliv|"
    r"Kaupr|Finanstilsynet|Finansinspektionen|Investornytt|hurbra|"
    r"Kryptovalutaguiden|Realtid|Breakit|Yle|Helsingin\s*Sanomat)\b",
    re.I,
)

# New styles are built from a technique plus the story topic. Each pair is a
# new library row. Ligne claire stays limited to original characters.
TECHNIQUES = (
    ("risograph", "risograph print, misregistered ink layers, limited colours, paper grain"),
    ("gouache", "opaque gouache painting, matte pigment, visible brush, gallery still"),
    ("woodcut", "hand-carved woodcut print, bold black shapes, cream paper"),
    ("charcoal", "charcoal and white chalk on grey paper, soft smudge, studio study"),
    ("pastel", "soft pastel on textured paper, dusty colour, gentle edges"),
    ("linocut", "two-colour linocut, carved white lines, inked teal and gold"),
    ("film-35", "35mm documentary film still, slight grain, available light"),
    ("aerial", "aerial documentary photograph, high oblique, clear daylight"),
    ("clay", "claymation still, handmade figurines, miniature set, soft studio light, original characters only"),
    ("blueprint", "architectural blueprint laid over a faint warm photograph, cyan lines, no readable words"),
    ("impasto", "oil impasto, thick paint, palette knife, muted Nordic colours"),
    ("long-exposure", "long-exposure night photograph, gold light trails, deep teal sky"),
    ("folk-weave", "abstract Nordic textile, woven wool, geometric bands, no letters"),
    ("silver-gelatin", "black and white silver-gelatin photograph, rich blacks, winter light"),
    ("ligne-claire-original",
     "ligne claire comic illustration, clean black outlines, flat colour, "
     "original adult characters invented for this scene only, no existing comic characters, "
     "no boy reporter, no white dog"),
)

SCENES = {
    "bitcoin": "a plain unmarked metal disc and a paper ledger on a pine table",
    "mining": "a low industrial hall of machines in snow, no signs",
    "crime": "a quiet stone courthouse square in winter, no flags, no readable signs",
    "aml": "a glass office at dusk with abstract charts, no readable numbers",
    "banking": "a granite public building and a wide stair, no name and no crest",
    "funds": "document folders and a brass lamp in a Nordic office",
    "policy": "an empty parliamentary chamber with wooden benches, no coat of arms",
    "tax": "a simple desk, a lamp and blank paper, no readable text",
    "cbdc": "a stone public building seen across a frozen river, no flag emblem",
    "regulation": "a committee room with empty chairs and a long table",
    "mica": "a hearing room with empty chairs, no flags",
    "payments": "a shop counter with unmarked coins, no brand",
    "stablecoins": "a row of identical plain tokens beside calm water",
    "defi": "wooden beads on a string, arranged as a network, not a screen",
    "tokenisation": "a vault shelf of sealed envelopes, no writing",
    "companies": "a modest Nordic office street in sleet",
    "business": "a modest Nordic office street in sleet",
    "events": "a small evening gathering in a community hall, original adult attendees, no famous faces",
    "community": "a small evening gathering in a community hall, original adult attendees",
    "consumer": "a kitchen table with a closed laptop and a warm lamp",
    "default": "an ordinary Nordic waterfront in winter light, no logos",
}

ACCENTS = ("winter dusk", "early morning", "overcast noon", "blue hour", "snow light", "late autumn")

NEGATIVE = (
    "No readable text, no logos, no watermarks, no newspaper mastheads, no brand marks, "
    "no flags, no copyrighted comic characters, no bitcoin symbol. "
    "Leave the top-right corner visually quiet for a later overlay."
)


def log(msg):
    print(f"[story-image] {msg}", file=sys.stderr, flush=True)


def _endpoint():
    account = os.environ.get("CF_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    token = os.environ.get("CF_AI_TOKEN") or os.environ.get("CLOUDFLARE_AI_TOKEN")
    return (account or "").strip(), (token or "").strip()


def ai_configured():
    account, token = _endpoint()
    return bool(account and token)


def _plain(text, limit=280):
    text = BANNED.sub("figure", OUTLETS.sub("a newsroom", " ".join(str(text or "").split())))
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return text


def primary_topic(item):
    topics = [str(t).lower() for t in ((item or {}).get("topics") or [])]
    for key in SCENES:
        if key in topics:
            return key
    return "default"


def remember_style(recent, style_id, keep=RECENT_LIMIT):
    out = [s for s in (recent or []) if s != style_id]
    out.append(style_id)
    return out[-keep:]


def eligible_styles(styles, recent):
    banned = set((recent or [])[-RECENT_LIMIT:])
    return [s for s in styles or [] if s.get("id") and s["id"] not in banned]


def derive_style(item, styles, recent):
    """A new library row from the article topic. The id is not already stored."""
    taken = {s.get("id") for s in styles or []}
    topic = primary_topic(item)
    scene = SCENES.get(topic) or SCENES["default"]
    used_techniques = set()
    for sid in recent or []:
        used_techniques.add(str(sid).split("-")[0])
    for row in styles or []:
        if row.get("technique"):
            used_techniques.add(row["technique"])
    accent = ACCENTS[len(taken) % len(ACCENTS)]
    ordered = [t for t in TECHNIQUES if t[0] not in used_techniques] or list(TECHNIQUES)
    for slug, fragment in ordered:
        n = 1
        while True:
            sid = f"{slug}-{topic}" if n == 1 else f"{slug}-{topic}-{n}"
            if sid not in taken:
                break
            n += 1
            if n > 50:
                sid = f"{slug}-{topic}-{len(taken) + 1}"
                break
        prompt = f"{fragment}. {accent}. Scene: {scene}. Wide 16:9 landscape. Original subjects only. {NEGATIVE}"
        return {
            "id": sid,
            "prompt": BANNED.sub("figure", prompt),
            "origin": "topic",
            "topic": topic,
            "technique": slug,
        }
    raise RuntimeError("could not derive a style")


def choose_style(styles, recent, item, rng=None):
    """A style dict. A new topic style when every stored style was used recently."""
    rng = rng or random.Random()
    choices = eligible_styles(styles, recent)
    if choices:
        return rng.choice(choices)
    return derive_style(item, styles, recent)


def story_prompt(item, style):
    title = _plain(item.get("title_en") or item.get("title") or "Nordic crypto news", 160)
    summary = _plain(item.get("summary") or item.get("summary_en") or "", 220)
    country = COUNTRY.get((item.get("country") or "").upper(), "the Nordics")
    scene = summary or f"a scene that evokes the news: {title}"
    fragment = style.get("prompt") if isinstance(style, dict) else str(style or "")
    prompt = (
        f"{fragment}. Wide 16:9 landscape. Subject inspired by this Nordic crypto news from {country}: "
        f"«{title}». Visual mood: {scene}. {NEGATIVE}"
    )
    return BANNED.sub("figure", prompt)[:2000]


def _call_model(body, account, token):
    model = os.environ.get("CF_IMAGE_MODEL") or MODEL
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "nordic-crypto-story-image/1 (+https://nordiccrypto.no/)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read()
    except urllib.error.HTTPError as err:
        detail = err.read()[:240].decode("utf-8", "replace")
        if token and token in detail:
            detail = detail.replace(token, "[token]")
        log(f"Workers AI HTTP {err.code}: {detail}")
        return None, err.code
    except Exception as err:
        log(f"Workers AI failed: {type(err).__name__}: {err}")
        return None, 0
    if "json" in ctype or (data[:1:] in (b"{", b"[")):
        try:
            res = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            log("Workers AI returned unreadable JSON")
            return None, 0
        result = res.get("result") if isinstance(res, dict) else None
        b64 = result.get("image") if isinstance(result, dict) else None
        if not b64 and isinstance(res, dict):
            b64 = res.get("image")
        if not b64:
            log("Workers AI returned no image")
            return None, 0
        try:
            return base64.b64decode(b64), 200
        except Exception:
            log("Workers AI image was not base64")
            return None, 0
    if data:
        return data, 200
    return None, 0


def generate_ai(prompt, *, seed=None):
    """flux-1-schnell bytes, or None when credentials are missing or the call fails."""
    account, token = _endpoint()
    if not account or not token:
        return None
    steps = int(os.environ.get("CF_IMAGE_STEPS") or 4)
    body = {"prompt": prompt[:2000], "steps": steps, "width": W, "height": H}
    if seed is not None:
        body["seed"] = int(seed)
    raw, code = _call_model(body, account, token)
    if raw is None and code == 400:
        body.pop("width", None)
        body.pop("height", None)
        raw, _code = _call_model(body, account, token)
    return raw


def _fit(im):
    from PIL import Image
    im = im.convert("RGB")
    scale = max(W / im.width, H / im.height)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - W) // 2, (nh - H) // 2
    return im.crop((left, top, left + W, top + H))


def brand_overlay(im):
    """«Nordic Crypto» (Nordic white, Crypto gold) in a teal pill, top-right."""
    from PIL import Image, ImageDraw, ImageFont
    im = im.convert("RGBA")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype(FONT_SERIF, 42)
    except OSError:
        font = ImageFont.load_default()
    nordic, crypto = "Nordic ", "Crypto"
    tw = draw.textlength(nordic, font=font) + draw.textlength(crypto, font=font)
    pad_x, pad_y, gap = 22, 14, 12
    mark_h = 40
    try:
        mark = Image.open(MARK).convert("RGBA")
        ratio = mark_h / mark.height
        mark = mark.resize((max(1, round(mark.width * ratio)), mark_h), Image.LANCZOS)
    except Exception:
        mark = None
    mark_w = mark.width if mark else 0
    box_w = int(pad_x * 2 + (mark_w + gap if mark else 0) + tw)
    box_h = int(pad_y * 2 + max(mark_h, 48))
    x1, y1 = W - 28 - box_w, 24
    x2, y2 = x1 + box_w, y1 + box_h
    draw.rounded_rectangle([x1 - 1, y1 - 1, x2 + 1, y2 + 1], radius=14, fill=GOLD + (255,))
    draw.rounded_rectangle([x1, y1, x2, y2], radius=13, fill=TEAL + (240,))
    tx = x1 + pad_x
    if mark:
        im.alpha_composite(mark, (tx, y1 + (box_h - mark_h) // 2))
        tx += mark_w + gap
    ty = y1 + box_h // 2
    draw.text((tx, ty), nordic, font=font, fill=WHITE + (255,), anchor="lm")
    draw.text((tx + draw.textlength(nordic, font=font), ty), crypto, font=font, fill=GOLD + (255,), anchor="lm")
    return im.convert("RGB")


def fallback_card(headline, subtitle=""):
    """Pillow brand card when Workers AI is unavailable."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), TEAL)
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, H - 12, W, H], fill=GOLD)
    try:
        big = ImageFont.truetype(FONT_SERIF, 64)
        small = ImageFont.truetype(FONT_SANS, 28)
    except OSError:
        big = small = ImageFont.load_default()
    maxw, pad = W - 120, 60
    words, lines, cur = (headline or "Nordic Crypto").split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=big) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    lines = lines[:4]
    y = 160
    draw.line([(pad, y), (pad + 120, y)], fill=GOLD, width=6)
    y += 36
    for line in lines:
        draw.text((pad, y), line, font=big, fill=WHITE)
        y += 76
    if subtitle:
        draw.text((pad, min(y + 20, H - 80)), _plain(subtitle, 90), font=small, fill=(0xD9, 0xE3, 0xE6))
    return im


def render(item, out_path, *, style, generator=None):
    """Write a branded PNG. Returns (kind, prompt) where kind is 'ai' or 'fallback'."""
    prompt = story_prompt(item, style if isinstance(style, dict) else {"prompt": str(style or "")})
    raw = (generator or generate_ai)(prompt)
    from PIL import Image
    kind = "ai"
    if raw:
        try:
            im = _fit(Image.open(io.BytesIO(raw)))
        except Exception as err:
            log(f"decode failed ({type(err).__name__}); using fallback card")
            raw = None
    if not raw:
        kind = "fallback"
        title = item.get("title_en") or item.get("title") or "Nordic Crypto"
        im = fallback_card(_plain(title, 120), "")
        log(f"fallback card ({style.get('id') if isinstance(style, dict) else style})")
    else:
        log(f"generated {style.get('id') if isinstance(style, dict) else style}")
    im = brand_overlay(im)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    im.save(out_path, "PNG", optimize=True)
    return kind, prompt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--story-json", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--style-prompt", default="photoreal editorial photography, natural Nordic light")
    a = ap.parse_args(argv)
    item = json.loads(a.story_json)
    kind, _prompt = render(item, a.out, style={"id": "cli", "prompt": a.style_prompt})
    print(a.out, kind)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:
        log(f"fatal: {type(err).__name__}: {err}")
        sys.exit(1)
