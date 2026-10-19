"""Google News: NewsArticle and Organization JSON-LD, sitemap lastmod, news-sitemap.xml and the sitemap index."""
import datetime as dt
import json
from xml.sax.saxutils import escape

NAME = "Nordic Crypto"
LOGO = "assets/brand/mark-512.png"   # the key shield, 512 x 512
NEWS_WINDOW = dt.timedelta(days=2)
NEWS_MAX = 1000
NEWS_LANG = {"zh": "zh-cn"}   # Google News: zh-cn / zh-tw; every other site code is ISO 639


def when(value):
    """An ISO date or datetime as an aware datetime (a date alone is noon UTC). None when it does not parse."""
    s = str(value or "").strip()
    if not s:
        return None
    try:
        if len(s) == 10:
            return dt.datetime.fromisoformat(s).replace(hour=12, tzinfo=dt.timezone.utc)
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def iso(value):
    d = when(value)
    return d.replace(microsecond=0).isoformat() if d else None


def published_here(item):
    """When the story went up on Nordic Crypto: the editor's approval, else the source time."""
    a, p = when(item.get("approved_at")), when(item.get("published"))
    if a and p and len(str(item.get("approved_at"))) == 10 and a.date() == p.date():
        a = max(a, p)   # a date-only approval on the source's own day
    return iso(a or p)


def publisher(base):
    return {"@type": "Organization", "name": NAME, "url": base,
            "logo": {"@type": "ImageObject", "url": base + LOGO, "width": 512, "height": 512}}


def desk(base):
    return {"@type": "Organization", "name": NAME, "url": base + "editorial/"}


def organization(base, email, same_as=()):
    org = publisher(base)
    org.update({
        "@type": "NewsMediaOrganization", "@id": base + "#organization", "email": email,
        "publishingPrinciples": base + "editorial/", "ethicsPolicy": base + "ethics/",
        "correctionsPolicy": base + "editorial/#corrections", "masthead": base + "about/#masthead",
        "parentOrganization": {"@type": "Organization", "name": "jQrgenCorp"},
        "contactPoint": {"@type": "ContactPoint", "contactType": "editorial", "email": email},
    })
    if same_as:
        org["sameAs"] = [u for u in same_as if u]
    return org


def news_article(*, url, headline, lang, published, base, image, description="", modified=None, sources=()):
    data = {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": headline[:110], "inLanguage": lang,
        "datePublished": published, "dateModified": modified or published,
        "author": [desk(base)], "publisher": publisher(base), "image": [image],
    }
    if description:
        data["description"] = description if len(description) <= 300 else description[:300].rsplit(" ", 1)[0] + "…"
    cites = [u for u in dict.fromkeys(sources) if u and str(u).startswith("http")]
    if cites:
        data["isBasedOn"] = cites[0]
        data["citation"] = cites
    return data


def ld_script(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("<", "\\u003c") + "</script>"


def urlset(urls, lastmod):
    rows = []
    for u in sorted(set(urls)):
        m = lastmod.get(u)
        rows.append(f"<url><loc>{escape(u)}</loc>" + (f"<lastmod>{m}</lastmod>" if m else "") + "</url>\n")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(rows) + "</urlset>\n")


def news_sitemap(entries, now):
    """entries: {url, lang, title, published}. Newest first, the last two days only, at most 1000."""
    cut = now - NEWS_WINDOW
    keep = [e for e in entries if when(e.get("published")) and cut <= when(e["published"]) <= now + dt.timedelta(minutes=5)]
    keep.sort(key=lambda e: when(e["published"]), reverse=True)
    rows = []
    for e in keep[:NEWS_MAX]:
        rows.append(f"<url><loc>{escape(e['url'])}</loc><news:news><news:publication><news:name>{NAME}</news:name>"
                    f"<news:language>{NEWS_LANG.get(e['lang'], e['lang'])}</news:language></news:publication>"
                    f"<news:publication_date>{iso(e['published'])}</news:publication_date>"
                    f"<news:title>{escape(e['title'])}</news:title></news:news></url>\n")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + "".join(rows) + "</urlset>\n")


def sitemap_index(base, files, lastmod=None):
    rows = "".join(f"<sitemap><loc>{escape(base + f)}</loc>" + (f"<lastmod>{lastmod}</lastmod>" if lastmod else "") + "</sitemap>\n" for f in files)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + rows + "</sitemapindex>\n")
