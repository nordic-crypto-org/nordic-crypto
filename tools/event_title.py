"""Event titles in every site language.

data/event_title_i18n.json: {id: {source, lang, <code>: title}}. source is the original title the
translations were made from, lang its language. Every site language except lang. An entry is used
only while source is the current original title. The editor's English title (title_en approval,
title_orig on the row) wins over the catalogue for English.

show() follows card_headline(): the title in the page language, the original underneath when it
differs, one title when the page reads the original language. A missing language falls back to English.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import i18n  # noqa: E402

PATH = os.path.join(ROOT, "data", "event_title_i18n.json")
_WS = re.compile(r"\s+")
_LOADED = {}


def norm(text):
    return _WS.sub(" ", (text or "").strip()).casefold()


def load(path=None):
    path = path or PATH
    try:
        st = os.stat(path)
        hit = _LOADED.get(path)
        if hit and hit[0] == (st.st_mtime_ns, st.st_size):
            return hit[1]
        items = json.load(open(path, encoding="utf-8")).get("items") or {}
    except FileNotFoundError:
        return {}
    _LOADED[path] = ((st.st_mtime_ns, st.st_size), items)
    return items


def original(event):
    return (event.get("title_orig") or event.get("title") or "").strip()


def entry(event, catalogue=None):
    cat = (load() if catalogue is None else catalogue).get(event.get("id")) or {}
    return cat if isinstance(cat, dict) and cat.get("source") == original(event) else {}


def source_lang(event, catalogue=None):
    rec = event.get("description") if isinstance(event.get("description"), dict) else {}
    return entry(event, catalogue).get("lang") or event.get("title_lang") or rec.get("lang") or None


def titles(event, catalogue=None):
    """{lang: title} that still belong to the original title, without the original's own language."""
    orig = original(event)
    cur = entry(event, catalogue)
    out = {l: cur[l].strip() for l in i18n.ALL_LANGS if isinstance(cur.get(l), str) and cur[l].strip()}
    if event.get("title_orig") and norm(event.get("title")) != norm(orig):
        out["en"] = event["title"].strip()
    out.pop(source_lang(event, catalogue), None)
    return {l: v for l, v in out.items() if norm(v) != norm(orig)}


def show(event, lang, catalogue=None):
    """(title, language code of that title, original or '')."""
    orig = original(event)
    src = source_lang(event, catalogue)
    if not orig or lang == src:
        return orig, src or lang, ""
    got = titles(event, catalogue)
    if not got.get(lang) and (entry(event, catalogue).get(lang) or "").strip():
        return orig, src or lang, ""  # the page-language title is the original
    line = got.get(lang) or got.get("en")
    if line:
        return line, (lang if got.get(lang) else "en"), orig
    return orig, src or lang, ""


def missing(event, catalogue=None):
    """Site languages that still need a title for this event."""
    orig = original(event)
    if not orig:
        return []
    cur = entry(event, catalogue)
    src = source_lang(event, catalogue)
    return [l for l in i18n.ALL_LANGS if l != src and not (cur.get(l) or "").strip()
            and not (l == "en" and event.get("title_orig"))]
