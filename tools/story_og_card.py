"""1200x630 link-preview card for a story page: headline on brand teal, «Nordic Crypto» top-right.
Optional licensed illustration (tools/illustrations.py) fills the left; never outlet logos.
Pillow is optional; without it the caller falls back to the site-wide og-image."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_B = os.path.join(ROOT, "assets", "fonts", "CormorantGaramond-SemiBold.ttf")
FONT_R = os.path.join(ROOT, "assets", "fonts", "SchibstedGrotesk-Medium.ttf")
MARK = os.path.join(ROOT, "assets", "brand", "mark-64.png")
TEAL, GOLD, WHITE = "#1E3A45", "#D9A034", "#F0F1EC"


def _wrap(draw, text, font, width):
    lines, cur = [], ""
    for w in (text or "").split():
        nxt = (cur + " " + w).strip()
        if draw.textlength(nxt, font=font) <= width or not cur:
            cur = nxt
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def covers(text):
    try:
        from PIL import ImageFont
    except ImportError:
        return True
    font = ImageFont.truetype(FONT_B, 40)
    def shape(c):
        m = font.getmask(c)
        return m.size, bytes(m)
    blank = shape("\ue000")
    return all(shape(c) != blank for c in set(text or "") if not c.isspace())


def render(path, title, subtitle="", illustration_path=None):
    """Write the card to path. Returns True when written, False when Pillow is missing."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    W, H, pad = 1200, 630, 56
    img = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 12, W, H], fill=GOLD)

    # optional illustration on the left third
    text_left = pad
    if illustration_path and os.path.isfile(illustration_path):
        try:
            pic = Image.open(illustration_path).convert("RGB")
            box_w, box_h = 420, H - 12
            scale = max(box_w / pic.width, box_h / pic.height)
            pic = pic.resize((round(pic.width * scale), round(pic.height * scale)), Image.LANCZOS)
            pic = pic.crop(((pic.width - box_w) // 2, (pic.height - box_h) // 2,
                            (pic.width - box_w) // 2 + box_w, (pic.height - box_h) // 2 + box_h))
            img.paste(pic, (0, 0))
            # fade into teal
            fade = Image.new("RGBA", (80, box_h), (0, 0, 0, 0))
            fd = ImageDraw.Draw(fade)
            for x in range(80):
                fd.line([(x, 0), (x, box_h)], fill=(0x1E, 0x3A, 0x45, int(x / 79 * 255)))
            img.paste(Image.alpha_composite(img.crop((box_w - 80, 0, box_w, box_h)).convert("RGBA"), fade).convert("RGB"),
                      (box_w - 80, 0))
            text_left = box_w + 36
        except Exception:
            text_left = pad

    # top-right brand chip
    try:
        chip_font = ImageFont.truetype(FONT_B, 28)
    except OSError:
        chip_font = ImageFont.load_default()
    label_n, label_c = "Nordic ", "Crypto"
    tw = d.textlength(label_n, font=chip_font) + d.textlength(label_c, font=chip_font)
    mark = None
    try:
        mark = Image.open(MARK).convert("RGBA")
        mh = 28
        r = mh / mark.height
        mark = mark.resize((max(1, round(mark.width * r)), mh), Image.LANCZOS)
    except Exception:
        mark = None
    mw = mark.width + 10 if mark else 0
    bw, bh = int(18 * 2 + mw + tw), 44
    x1, y1 = W - 24 - bw, 20
    d.rounded_rectangle([x1 - 1, y1 - 1, x1 + bw + 1, y1 + bh + 1], radius=12, fill=GOLD)
    d.rounded_rectangle([x1, y1, x1 + bw, y1 + bh], radius=11, fill=TEAL)
    tx = x1 + 14
    if mark:
        img.paste(mark, (tx, y1 + (bh - mark.height) // 2), mark)
        tx += mw
    d.text((tx, y1 + bh // 2), label_n, font=chip_font, fill=WHITE, anchor="lm")
    d.text((tx + d.textlength(label_n, font=chip_font), y1 + bh // 2), label_c, font=chip_font, fill=GOLD, anchor="lm")

    size = 64
    maxw = W - text_left - pad
    while True:
        big = ImageFont.truetype(FONT_B, size)
        lines = _wrap(d, title, big, maxw)
        if len(lines) <= 4 or size <= 40:
            break
        size -= 4
    lines = lines[:4]
    y = 150
    d.line([(text_left, y), (text_left + 100, y)], fill=GOLD, width=5)
    y += 28
    for ln in lines:
        d.text((text_left, y), ln, font=big, fill="#FFFFFF"); y += int(size * 1.15)
    small = ImageFont.truetype(FONT_R, 26)
    subtitle = (subtitle or "").replace("·", "-").replace("–", "-")
    if subtitle:
        if d.textlength(subtitle, font=small) > maxw:
            while subtitle and d.textlength(subtitle + "…", font=small) > maxw:
                subtitle = subtitle[:-1]
            subtitle = subtitle.rstrip() + "…"
        d.text((text_left, H - pad - 36), subtitle, font=small, fill="#D9E3E6")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return True
