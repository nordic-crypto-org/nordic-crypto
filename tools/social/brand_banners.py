"""Render Nordic Crypto profile/cover art: Facebook profile (1080x1080), Facebook cover (1640x624), YouTube banner (2048x1152).
Usage: python3 tools/social/brand_banners.py [OUT_DIR]   (font: NC_STORY_FONT)"""
import io, os, sys, cairosvg
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG = os.path.join(ROOT, 'assets', 'brand', 'icon.svg')
F = os.environ.get('NC_STORY_FONT', '/usr/share/fonts/truetype/sand-box/google/Inter/Inter-VariableFont_opsz,wght.ttf')
T = (0x1E, 0x3A, 0x45); G = (0xD9, 0xA0, 0x34); W = (0xF0, 0xF1, 0xEC)
LINES = ("Nordic Crypto", "Bitcoin, blockchain og krypto fra Norden", "nordiccrypto.no")

def logo(h):
    s = open(SVG).read().replace('<rect width="64" height="64" rx="14" fill="#1E3A45"/>', '')
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode(), output_width=h*2, output_height=h*2))).convert('RGBA')
    im = im.crop(im.getbbox()); r = h / im.height
    return im.resize((round(im.width*r), h), Image.LANCZOS)

def font(sz, w):
    f = ImageFont.truetype(F, sz)
    try: f.set_variation_by_axes([32, w])
    except Exception: f.set_variation_by_axes([w])
    return f

def profile(out):
    p = Image.new('RGBA', (1080, 1080), T + (255,)); L = logo(600)
    p.alpha_composite(L, ((1080-L.width)//2, (1080-L.height)//2)); p.convert('RGB').save(out)

def banner(out, w, h, lh, sizes, gap, yoff, dys, rule):
    c = Image.new('RGBA', (w, h), T + (255,)); d = ImageDraw.Draw(c); L = logo(lh)
    fs = [font(sizes[0], 800), font(sizes[1], 500), font(sizes[2], 700)]
    lines = list(zip(LINES, fs, (W, W, G)))
    tw = max(d.textlength(t, font=f) for t, f, _ in lines)
    x0 = (w - (L.width + gap + tw)) // 2; c.alpha_composite(L, (int(x0), (h - L.height)//2))
    y = h//2 - yoff; tx = x0 + L.width + gap
    for (t, f, col), dy in zip(lines, dys): d.text((tx, y+dy), t, font=f, fill=col)
    d.line([(tx, y+rule), (tx+120, y+rule)], fill=G, width=5)
    c.convert('RGB').save(out)

if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(o, exist_ok=True)
    profile(os.path.join(o, 'nordic-crypto-fb-profile.png'))
    banner(os.path.join(o, 'nordic-crypto-fb-cover.png'), 1640, 624, 250, (96, 38, 32), 50, 125, (0, 135, 200), 118)
    banner(os.path.join(o, 'nordic-crypto-yt-banner.png'), 2048, 1152, 230, (92, 36, 30), 46, 118, (0, 128, 190), 112)
