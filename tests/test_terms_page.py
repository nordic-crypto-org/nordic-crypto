#!/usr/bin/env python3
"""Terms of use (terms/) for every language, linked in the footer, and the TikTok OAuth callback (tiktok/callback/):
English only, noindex, not in sitemap.xml, sends the code nowhere. No network.
  python3 tests/test_terms_page.py
"""
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build  # noqa: E402
import i18n  # noqa: E402

fails = []


def check(ok, msg):
    print(("ok  " if ok else "FAIL") + " " + msg)
    if not ok:
        fails.append(msg)


def main():
    for name in ("terms.html", "terms.nb.html", "terms.nn.html"):
        text = open(os.path.join(ROOT, "templates", name), encoding="utf-8").read()
        for sid in ("who", "advice", "rights", "affiliation", "tiktok", "law"):
            check(f'<h2 id="{sid}">' in text, f"{name}: #{sid}")
        check("jqrgen@nordiccrypto.no" in text and not re.search(r"\+47|tel:", text), name + ": email only, no phone")
    for name in ("privacy.html", "privacy.nb.html", "privacy.nn.html"):
        check('<h2 id="tiktok">' in open(os.path.join(ROOT, "templates", name), encoding="utf-8").read(), name + ": #tiktok")
    for lang in i18n.ALL_LANGS:
        for k in ("tos_title", "tos_desc", "tos_note"):
            check(i18n.has(lang, k), f"{lang}: {k}")

    with tempfile.TemporaryDirectory() as tmp:
        build.SITE = tmp
        for lang in ("en", "nb", "nn", "de", "ar"):
            build.LANG = lang
            build.build_terms()
            build.build_tiktok_callback()
            path = os.path.join(tmp, *([] if lang == "en" else [lang]), "terms", "index.html")
            check(os.path.exists(path), f"{lang}: terms/index.html written")
            if not os.path.exists(path):
                continue
            html = open(path, encoding="utf-8").read()
            check("{{" not in html, f"{lang}: no placeholder left")
            check(re.search(r'href="[./a-z]*terms/"', html) and build.E(build.t("tos_title")) in html, f"{lang}: footer link")
            check((build.E(build.t("tos_note")) in html) == (lang in ("de", "ar")), f"{lang}: fallback note only on English text")
            check(os.path.exists(os.path.join(tmp, lang, "tiktok")) is False, f"{lang}: no translated callback")
        cb = open(os.path.join(tmp, "tiktok", "callback", "index.html"), encoding="utf-8").read()
        check('content="noindex, nofollow"' in cb, "callback: noindex")
        check(not re.search(r"fetch\(|XMLHttpRequest|sendBeacon", cb.split("</main>")[0]), "callback: sends nothing")
        check("history.replaceState" in cb, "callback: query removed from the address bar")
        build.sitemap()
        check("tiktok/" not in open(os.path.join(tmp, "sitemap.xml"), encoding="utf-8").read(), "callback: not in sitemap.xml")
    print(f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
