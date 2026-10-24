"""Render Telegram avatars: group.png (Nordic cross) and bot.png (cross + NEWS badge), plus round previews.
Usage: python3 tools/social/telegram_avatars.py [OUT_DIR]"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
S = 1024; BLUE = (15, 94, 168); INK = (17, 17, 17); W = (255, 255, 255)
F = os.environ.get('NC_TG_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')

def cross(d, col, cx, cy, th):
    d.rectangle([cx-th//2, 0, cx+th//2, S], fill=col)
    d.rectangle([0, cy-th//2, S, cy+th//2], fill=col)

def main(o):
    os.makedirs(o, exist_ok=True); p = lambda n: os.path.join(o, n)
    g = Image.new('RGB', (S, S), BLUE); cross(ImageDraw.Draw(g), W, int(S*0.40), S//2, int(S*0.17)); g.save(p('group.png'))
    b = Image.new('RGB', (S, S), INK); d = ImageDraw.Draw(b)
    cx, cy = int(S*0.40), int(S*0.44)
    cross(d, W, cx, cy, int(S*0.20)); cross(d, BLUE, cx, cy, int(S*0.12))
    f = ImageFont.truetype(F, 118); t = 'NEWS'
    bw = d.textbbox((0, 0), t, font=f); tw = bw[2]-bw[0]; th = bw[3]-bw[1]
    x = (S-tw)//2; y = int(S*0.70)
    d.rounded_rectangle([x-40, y-28, x+tw+40, y+th+52], radius=28, fill=W)
    d.text((x-bw[0], y-bw[1]+12), t, font=f, fill=INK); b.save(p('bot.png'))
    for n in ('group', 'bot'):
        im = Image.open(p(n+'.png')).resize((256, 256)); m = Image.new('L', (256, 256), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 255, 255], fill=255)
        bg = Image.new('RGB', (256, 256), (240, 240, 240)); bg.paste(im, (0, 0), m); bg.save(p(n+'-preview.png'))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
