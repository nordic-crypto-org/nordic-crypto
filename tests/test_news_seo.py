#!/usr/bin/env python3
"""Google News: news-sitemap.xml, sitemap lastmod, NewsArticle / Organization JSON-LD and /editorial/.
The site checks read a built site/ (or NC_SITE_DIR) and are skipped when there is none.
  python3 -m unittest tests.test_news_seo"""
import datetime as dt
import glob
import json
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools import news_seo  # noqa: E402
import i18n  # noqa: E402

BASE = "https://nordiccrypto.no/"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "n": "http://www.google.com/schemas/sitemap-news/0.9"}
NOW = dt.datetime(2026, 10, 19, 12, 0, tzinfo=dt.timezone.utc)
SITE = os.environ.get("NC_SITE_DIR") or os.path.join(ROOT, "site")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Units(unittest.TestCase):
    def test_news_sitemap_window_limit_and_fields(self):
        rows = [{"url": BASE + f"stories/{n}/", "lang": "en", "title": f"T {n} & co", "published": (NOW - dt.timedelta(hours=n)).isoformat()} for n in range(60)]
        rows.append({"url": BASE + "zh/stories/x/", "lang": "zh", "title": "中文", "published": NOW.isoformat()})
        root = ET.fromstring(news_seo.news_sitemap(rows, NOW))
        urls = root.findall("s:url", NS)
        self.assertEqual(len(urls), 49 + 1)   # 0..48 hours, plus the Chinese page
        first = urls[0].find("n:news", NS)
        self.assertEqual(first.find("n:publication/n:name", NS).text, "Nordic Crypto")
        langs = {u.find("n:news/n:publication/n:language", NS).text for u in urls}
        self.assertEqual(langs, {"en", "zh-cn"})
        self.assertTrue(all(u.find("n:news/n:title", NS).text for u in urls))
        many = [dict(rows[0], url=BASE + f"x/{n}/") for n in range(1200)]
        self.assertEqual(len(ET.fromstring(news_seo.news_sitemap(many, NOW)).findall("s:url", NS)), 1000)

    def test_urlset_lastmod_only_when_known(self):
        root = ET.fromstring(news_seo.urlset([BASE, BASE + "about/"], {BASE: "2026-10-19T04:44:11+02:00"}))
        got = {u.find("s:loc", NS).text: getattr(u.find("s:lastmod", NS), "text", None) for u in root.findall("s:url", NS)}
        self.assertEqual(got, {BASE: "2026-10-19T04:44:11+02:00", BASE + "about/": None})

    def test_published_here(self):
        self.assertEqual(news_seo.published_here({"published": "2026-10-18T14:49:35+00:00", "approved_at": "2026-10-19T04:44:11+02:00"}), "2026-10-19T04:44:11+02:00")
        self.assertEqual(news_seo.published_here({"published": "2026-10-18T14:49:35+00:00"}), "2026-10-18T14:49:35+00:00")
        self.assertEqual(news_seo.published_here({"published": "2026-10-18T14:49:35+00:00", "approved_at": "2026-10-18"}), "2026-10-18T14:49:35+00:00")

    def test_news_article(self):
        d = news_seo.news_article(url=BASE + "stories/a/", headline="H", lang="en", published="2026-10-19T04:44:11+02:00", base=BASE,
                                  image=BASE + "assets/brand/og-image.png", sources=["https://example.no/a", None, "https://example.no/a", "https://reg.no/b"])
        self.assertEqual(d["@type"], "NewsArticle")
        self.assertEqual([a["@type"] for a in d["author"]], ["Organization"])
        self.assertEqual(d["publisher"]["name"], "Nordic Crypto")
        self.assertTrue(d["publisher"]["logo"]["url"].endswith("assets/brand/mark-512.png"))
        self.assertEqual(d["isBasedOn"], "https://example.no/a")
        self.assertEqual(d["citation"], ["https://example.no/a", "https://reg.no/b"])
        self.assertEqual(d["dateModified"], d["datePublished"])
        self.assertNotIn("<", news_seo.ld_script({"x": "</script>"})[35:-9])

    def test_editorial_in_every_language(self):
        for lang in i18n.ALL_LANGS:
            path = os.path.join(ROOT, "templates", "editorial.html" if lang == "en" else f"editorial.{lang}.html")
            self.assertTrue(os.path.exists(path), lang)
            text = read(path)
            for anchor in ("who", "selection", "summaries", "sources", "ai", "corrections", "conflicts", "contact"):
                self.assertIn(f'id="{anchor}"', text, (lang, anchor))
            self.assertIn("mailto:jqrgen@nordiccrypto.no", text, lang)
            self.assertNotRegex(text, r"919\s?057\s?343|\+47|org\.?\s?n", lang)
            for key in ("ed_title", "ed_desc", "ed_desk", "ed_byline"):
                self.assertIn(key, i18n.strings(lang), (lang, key))
            self.assertIn("{desk}", i18n.strings(lang)["ed_byline"])


def _ld(html, kind):
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        d = json.loads(raw)
        if d.get("@type") == kind:
            return d
    return None


@unittest.skipUnless(os.path.exists(os.path.join(SITE, "sitemap.xml")), "no built site")
class Site(unittest.TestCase):
    def test_robots_and_index(self):
        robots = read(os.path.join(SITE, "robots.txt"))
        for f in ("sitemap-index.xml", "sitemap.xml", "news-sitemap.xml"):
            self.assertIn(f"Sitemap: {BASE}{f}", robots)
        locs = [e.text for e in ET.parse(os.path.join(SITE, "sitemap-index.xml")).getroot().iter("{%s}loc" % NS["s"])]
        self.assertEqual(locs, [BASE + "sitemap.xml", BASE + "news-sitemap.xml"])

    def test_news_sitemap_parses(self):
        root = ET.parse(os.path.join(SITE, "news-sitemap.xml")).getroot()
        urls = root.findall("s:url", NS)
        self.assertLessEqual(len(urls), 1000)
        for u in urls:
            loc = u.find("s:loc", NS).text
            self.assertTrue(loc.startswith(BASE) and "/stories/" in loc, loc)
            self.assertIsNotNone(news_seo.when(u.find("n:news/n:publication_date", NS).text))

    def test_story_pages_have_news_article(self):
        pages = sorted(glob.glob(os.path.join(SITE, "stories", "*", "index.html")))
        self.assertTrue(pages)
        for p in pages[:20]:
            html = read(p)
            d = _ld(html, "NewsArticle")
            self.assertIsNotNone(d, p)
            for k in ("headline", "datePublished", "dateModified", "author", "publisher", "image", "mainEntityOfPage"):
                self.assertTrue(d.get(k), (p, k))
            self.assertIn('class="meta byline-desk"', html)
            self.assertIn(f'datetime="{d["datePublished"]}"', html)

    def test_home_and_editorial(self):
        org = _ld(read(os.path.join(SITE, "index.html")), "NewsMediaOrganization")
        self.assertEqual(org["name"], "Nordic Crypto")
        for lang in i18n.LANGS:
            pre = "" if lang == "en" else lang + "/"
            self.assertTrue(os.path.exists(os.path.join(SITE, pre, "editorial", "index.html")), lang)
        about = read(os.path.join(SITE, "about", "index.html"))
        self.assertIn('id="masthead"', about)
        self.assertIn('href="../editorial/"', about)
        sm = read(os.path.join(SITE, "sitemap.xml"))
        self.assertIn(f"<loc>{BASE}editorial/</loc>", sm)
        self.assertIn("<lastmod>", sm)


if __name__ == "__main__":
    unittest.main()
