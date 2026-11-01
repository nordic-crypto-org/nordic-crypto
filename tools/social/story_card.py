"""Render a 1080x1920 Facebook story image for a Nordic Crypto story.
Usage: python3 tools/social/story_card.py [--en] <headline> <source_name> <out.png> [summary] [url]
Font: Inter variable (override with NC_STORY_FONT)."""
import os, sys, io, cairosvg
from PIL import Image, ImageDraw, ImageFont
W_, H_ = 1080, 1920
SAFE = 250; SIDE = 90
T=(0x1E,0x3A,0x45); G=(0xD9,0xA0,0x34); W=(0xF0,0xF1,0xEC)
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F=os.environ.get('NC_STORY_FONT','/usr/share/fonts/truetype/sand-box/google/Inter/Inter-VariableFont_opsz,wght.ttf')
SVG=os.path.join(ROOT,'assets','brand','icon.svg')
def font(sz,w):
    f=ImageFont.truetype(F,sz)
    try: f.set_variation_by_axes([32,w])
    except Exception: f.set_variation_by_axes([w])
    return f
def logo(h):
    s=open(SVG).read().replace('<rect width="64" height="64" rx="14" fill="#1E3A45"/>','')
    im=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode(),output_width=h*2,output_height=h*2))).convert('RGBA')
    im=im.crop(im.getbbox()); r=h/im.height
    return im.resize((round(im.width*r),h),Image.LANCZOS)
def wrap(d,text,f,maxw):
    lines=[];cur=''
    for w in text.split():
        t=(cur+' '+w).strip()
        if d.textlength(t,font=f)<=maxw: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines
TXT={'no':('Kilde: ','Les mer på nordiccrypto.no'),'en':('Source: ','Read more at nordiccrypto.no')}
def render(headline, source, out, summary='', url='', lang='no'):
    src_lbl,more=TXT[lang]
    im=Image.new('RGBA',(W_,H_),T+(255,)); d=ImageDraw.Draw(im)
    maxw=W_-2*SIDE
    L=logo(150); y=SAFE
    im.alpha_composite(L,(SIDE,y))
    d.text((SIDE+L.width+36,y+L.height//2),"Nordic Crypto",font=font(56,800),fill=W,anchor='lm')
    top=y+L.height+90
    bottom_block=H_-SAFE-200
    for sz in (84,76,68,60,54,48,44):
        f=font(sz,800); lines=wrap(d,headline,f,maxw); lh=int(sz*1.22)
        if top+len(lines)*lh+60+80 <= bottom_block and all(d.textlength(l,font=f)<=maxw for l in lines): break
    d.line([(SIDE,top),(SIDE+140,top)],fill=G,width=8)
    ty=top+50
    for ln in lines:
        d.text((SIDE,ty),ln,font=f,fill=W); ty+=lh
    d.text((SIDE,ty+40),src_lbl+source,font=font(40,500),fill=G)
    fy=H_-SAFE
    # bottom block: QR + read-more + URL, all above the bottom safe zone
    ub=fy
    if url:
        disp=url.replace('https://','').rstrip('/')
        uf=font(36,600)
        for sz in (36,32,28):
            uf=font(sz,600)
            if d.textlength(disp,font=uf)<=maxw: break
        d.text((W_//2,ub-20),disp,font=uf,fill=W,anchor='md'); ub-=80
    d.text((W_//2,ub-20),more,font=font(48,700),fill=G,anchor='md'); ub-=90
    if summary:
        sy=ty+40+80; avail=ub-40-sy
        for sz in (48,46,44,42,40,38):
            sf=font(sz,400); sl=wrap(d,summary,sf,maxw); slh=int(sz*1.4)
            if len(sl)*slh<=avail: break
        n=max(1,avail//slh)
        if len(sl)>n:
            words=summary.split(); fit=[]
            while words:
                t=' '.join(fit+words[:1])+' …'
                if len(wrap(d,t,sf,maxw))>n: break
                fit.append(words.pop(0))
            sl=wrap(d,' '.join(fit).rstrip(',.;:')+' …',sf,maxw)
        for ln in sl:
            d.text((SIDE,sy),ln,font=sf,fill=W); sy+=slh
    im.convert('RGB').save(out)
if __name__=='__main__':
    a=sys.argv[1:]; lang='no'
    if a and a[0]=='--en': a=a[1:]; lang='en'
    render(*a[:5],lang=lang)
