#!/usr/bin/env python3
"""Checks the RSS feeds without a full build:
  - /rss.xml and /{lang}/rss.xml: <link> and <guid> point to our own story page, the original outlet is credited in
    <description> and in <source url=...>, and items without a story page are left out.
  - /newsletter/rss.xml and /{lang}/newsletter/rss.xml: one item per published issue, linking to the issue page.
  python3 tests/test_rss_feeds.py"""
import os, sys, tempfile, html
import xml.etree.ElementTree as ET
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build

fails = []
def ok(cond, msg):
    if not cond: fails.append(msg)

ITEMS = [
    {"id": "abc123", "status": "published", "title": "Kryptokamp i Kautokeino", "title_en": "Crypto camp in Kautokeino",
     "url": "https://altaposten.no/nyheter/n/x", "source_name": "Altaposten", "language": "Norwegian", "published": "2026-10-15T10:30:00+00:00",
     "summary": "English summary.", "summary_i18n": {"nb": "Norsk sammendrag."},
     "title_i18n": {"de": "Kryptocamp in Kautokeino"}},
    {"id": "nopage", "status": "published", "title": "No page", "url": "https://example.com/a", "source_name": "Ex",
     "published": "2026-10-14T10:00:00+00:00", "summary": "x"},
    {"id": "story-own", "status": "published", "title": "Own story", "url": "stories/own/", "own_story": True,
     "source_name": "Nordic Crypto", "published": "2026-10-13T10:00:00+00:00", "summary": "Ours."},
]
ISSUES = [{"id": "002", "number": 2, "date": "2026-10-12", "title": "Issue two", "subtitle": "Week 41.", "lang": "en",
           "title_i18n": {"de": "Ausgabe zwei"}, "subtitle_i18n": {"de": "Woche 41."}},
          {"id": "009", "number": 9, "date": "2026-12-01", "title": "No page yet", "subtitle": "x", "lang": "en"}]

with tempfile.TemporaryDirectory() as tmp:
    build.SITE = tmp
    base = build.BASE
    for lang in ("en", "nb", "de"):
        build.LANG = lang
        pre = "" if lang == "en" else lang + "/"
        build.PAGES_WRITTEN.clear()
        build.PAGES_WRITTEN.update({(lang, "stories/abc123"), (lang, "stories/own"), (lang, "newsletter/002")})
        build.write_rss(ITEMS)
        build.write_newsletter_rss(ISSUES)
        d = os.path.join(tmp, pre)
        root = ET.parse(os.path.join(d, "rss.xml")).getroot()   # raises when not well-formed
        items = root.findall("./channel/item")
        links = [i.findtext("link") for i in items]
        ok(links == [f"{base}{pre}stories/abc123/", f"{base}{pre}stories/own/"], f"{lang} story links {links}")
        first = items[0]
        g = first.find("guid")
        ok(g.text == links[0] and g.get("isPermaLink") == "true", f"{lang} guid is our permalink")
        src = first.find("source")
        ok(src is not None and src.get("url") == "https://altaposten.no/nyheter/n/x" and src.text == "Altaposten", f"{lang} <source>")
        desc = first.findtext("description")
        ok('href="https://altaposten.no/nyheter/n/x"' in desc and ">Altaposten</a>" in desc, f"{lang} description credits source")
        ok(build.t("source") + ":" in desc, f"{lang} source label")
        ok(("Norsk sammendrag." if lang == "nb" else "English summary.") in desc, f"{lang} summary")
        want = {"en": "Crypto camp in Kautokeino", "nb": "Kryptokamp i Kautokeino", "de": "Kryptocamp in Kautokeino"}[lang]
        ok(first.findtext("title") == want, f"{lang} item title in page language: {first.findtext('title')}")
        ok(root.findtext("./channel/description") == build.t("home_desc"), f"{lang} channel description")
        ok(items[1].find("source") is None, f"{lang} own story has no external <source>")
        ok(all("altaposten" not in (i.findtext("link") + i.findtext("guid")) for i in items), f"{lang} no source URL in link/guid")
        nl = ET.parse(os.path.join(d, "newsletter", "rss.xml")).getroot()
        nis = nl.findall("./channel/item")
        ok([i.findtext("link") for i in nis] == [f"{base}{pre}newsletter/002/"], f"{lang} newsletter items")
        ok(nis and nis[0].findtext("pubDate", "").startswith("Mon, 12 Oct 2026"), f"{lang} newsletter pubDate")
        ok(nis and nis[0].findtext("description") == ("Woche 41." if lang == "de" else "Week 41."), f"{lang} newsletter summary")
        ok(nis and nis[0].findtext("title") == ("Ausgabe zwei" if lang == "de" else "Issue two"), f"{lang} newsletter item title")
        ok(nl.findtext("./channel/title") == build.nl_feed_title() and build.t("nav_newsletter") in build.nl_feed_title(), f"{lang} newsletter channel title")
        ok(nl.findtext("./channel/language") == build.i18n.HTML_LANG[lang], f"{lang} newsletter channel language")

if fails:
    print("FAILED"); [print(" -", f) for f in fails]; sys.exit(1)
print("ok")
