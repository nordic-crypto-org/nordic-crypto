"""X (Twitter) avatar + header for Crypto Nordic (avatar.png 400x400, header.png 1500x500).
Usage: python3 tools/social/x_assets.py [OUT_DIR]"""
import os, sys
from playwright.sync_api import sync_playwright
BLUE = "#0f5ea8"
FONT = "font-family:system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif"
MARK = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' width='{{s}}' height='{{s}}'><rect width='16' height='16' fill='{BLUE}'/><rect x='4' width='3' height='16' fill='white'/><rect y='6.5' width='16' height='3' fill='white'/></svg>"
WORD = f"<span style='white-space:nowrap'>Crypto&nbsp;<span style='color:{BLUE}'>Nordic</span></span>"
D = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/") + "/"; os.makedirs(D, exist_ok=True)
avatar = f"<div style='width:400px;height:400px'>{MARK.format(s=400)}</div>"
header = (f"<div style='position:relative;width:1500px;height:500px;background:#f5f7fa;{FONT};overflow:hidden'>"
          f"<div style='position:absolute;left:0;top:0;width:1500px;height:14px;background:{BLUE}'></div>"
          f"<div style='position:absolute;left:300px;right:150px;top:90px;height:280px;display:flex;align-items:center;justify-content:center;gap:48px'>"
          f"<div style='width:170px;height:170px;flex:none'>{MARK.format(s=170)}</div>"
          f"<div><div style='font-weight:800;font-size:104px;letter-spacing:-2px;color:#111;line-height:1.1'>{WORD}</div>"
          f"<div style='font-size:38px;color:#4B5563;margin-top:10px'>Crypto news from the Nordics</div>"
          f"<div style='font-size:32px;font-weight:700;color:{BLUE};margin-top:14px'>cryptonordic.no</div></div></div></div>")
with sync_playwright() as p:
    b = p.chromium.launch()
    for path, w, h, html in ((D + "avatar.png", 400, 400, avatar), (D + "header.png", 1500, 500, header)):
        pg = b.new_page(viewport={"width": w, "height": h}); pg.set_content(f"<html><body style='margin:0'>{html}</body></html>"); pg.wait_for_timeout(200)
        pg.screenshot(path=path, clip={"x": 0, "y": 0, "width": w, "height": h}); pg.close(); print(path)
    b.close()
