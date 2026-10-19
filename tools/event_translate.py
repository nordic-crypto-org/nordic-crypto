#!/usr/bin/env python3
"""Fill data/event_description_i18n.json for event descriptions and data/event_title_i18n.json for event
titles (every site language) that have no current translation.

Cloudflare Workers AI (CF_AI_TOKEN, CF_ACCOUNT_ID; model CF_AI_MODEL).
Without them, or when a call fails, nothing is written for that event.
An entry is replaced only when its source no longer matches the description; existing languages are kept.

  python3 tools/event_translate.py [--dry-run]
"""
import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import i18n  # noqa: E402
from tools import event_description as ed, event_title as et  # noqa: E402

NAMES = {"en": "English", "nn": "Norwegian Nynorsk", "nb": "Norwegian Bokmål", "sv": "Swedish", "da": "Danish", "fi": "Finnish", "is": "Icelandic",
         "zh": "Simplified Chinese", "hi": "Hindi", "es": "Spanish", "fr": "French", "ar": "Arabic", "bn": "Bengali", "pt": "Portuguese",
         "ru": "Russian", "ur": "Urdu", "id": "Indonesian", "de": "German", "ja": "Japanese", "sw": "Swahili", "mr": "Marathi",
         "fa": "Persian", "uk": "Ukrainian", "tr": "Turkish"}
TITLE_PROMPT = ("Translate this event title into each language below. Return JSON only: {{\"lang\": the code of the title's own "
                "language, then code: title}} for the codes {codes}. Keep names of people, venues, organisers, projects and Nordic "
                "Crypto unchanged. A headline, not a sentence; nothing added.")
PROMPT = ("Translate this event description from {src} into each language below. Return JSON only: {{code: text}} for "
          "the codes {codes}. Keep names of people, venues, organisers and Nordic Crypto unchanged. Plain style, nothing added.")


def missing(event, catalogue):
    text, src = ed.stored(event)
    if not text or src not in ed.KNOWN:
        return text, src, []
    cur = catalogue.get(event.get("id")) or {}
    have = cur if cur.get("source") == text else {}
    return text, src, [l for l in ed.KNOWN if l != src and not (have.get(l) or "").strip()]


MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
ENV = ("CF_AI_TOKEN", "CF_ACCOUNT_ID")


def call_model(text, src, langs, system=None):
    account, token = os.environ["CF_ACCOUNT_ID"], os.environ["CF_AI_TOKEN"]
    model = os.environ.get("CF_AI_MODEL") or MODEL
    codes = ", ".join(f"{l} ({NAMES[l]})" for l in langs)
    body = {"temperature": 0.2, "max_tokens": 4096,
            "messages": [{"role": "system", "content": (system or PROMPT).format(src=NAMES.get(src, "the original language"), codes=codes)},
                         {"role": "user", "content": text}]}
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.load(r)["result"]["response"]
    if isinstance(out, dict):
        return out
    out = re.sub(r"^```(?:json)?|```$", "", out.strip()).strip()
    return json.loads(out[out.find("{"):out.rfind("}") + 1])


def fill(events, catalogue, translate=call_model, log=print):
    """Adds translations to catalogue in place. Returns the ids that changed."""
    changed = []
    for e in events:
        text, src, langs = missing(e, catalogue)
        if not langs:
            continue
        try:
            got = translate(text, src, langs)
        except Exception as err:  # one bad event must not stop the fetch
            log(f"event-translate {e.get('id')}: {err}")
            continue
        cur = catalogue.get(e["id"]) or {}
        entry = dict(cur) if cur.get("source") == text else {"source": text}
        for l in langs:
            v = ed.clean_description(got.get(l) or "") if isinstance(got, dict) else ""
            if v and ed.norm(v) != ed.norm(text):
                entry[l] = v
        if len(entry) > 1:
            catalogue[e["id"]] = entry
            changed.append(e["id"])
    return changed


def call_title_model(title, src, langs):
    return call_model(title, src, langs, TITLE_PROMPT)


def fill_titles(events, catalogue, translate=call_title_model, log=print):
    """Title in every site language except the title's own. Adds to catalogue in place; returns the ids that changed."""
    changed = []
    for e in events:
        langs = et.missing(e, catalogue)
        if not e.get("id") or not langs:
            continue
        title = et.original(e)
        try:
            got = translate(title, et.source_lang(e, catalogue), langs)
        except Exception as err:
            log(f"event-translate title {e.get('id')}: {err}")
            continue
        if not isinstance(got, dict):
            continue
        cur = et.entry(e, catalogue)
        src = cur.get("lang") or et.source_lang(e, catalogue) or (got.get("lang") if got.get("lang") in i18n.ALL_LANGS else None)
        if not src:
            continue
        new = dict(cur) if cur else {"source": title, "lang": src}
        for l in langs:
            v = " ".join(str(got.get(l) or "").split())
            if l != src and v and len(v) <= 3 * len(title) + 40:
                new[l] = v
        if new != cur:
            catalogue[e["id"]] = new
            changed.append(e["id"])
    return changed


def _save(path, doc):
    tmp = path + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def run(root=ROOT, log=print, translate=None, dry=False, translate_title=None):
    if translate is None:
        if not all(os.environ.get(k) for k in ENV):
            log("event-translate: CF_AI_TOKEN or CF_ACCOUNT_ID not set, skipped")
            return []
        translate, translate_title = call_model, call_title_model
    path = os.path.join(root, "data", "event_description_i18n.json")
    doc = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"items": {}}
    events = json.load(open(os.path.join(root, "data", "events.json"), encoding="utf-8")).get("events", [])
    changed = fill(events, doc.setdefault("items", {}), translate, log)
    if changed and not dry:
        _save(path, doc)
    log(f"event-translate: {len(changed)} descriptions translated")
    tpath = os.path.join(root, "data", "event_title_i18n.json")
    tdoc = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else {"_note": "Event titles in every site language.", "items": {}}
    bpath = os.path.join(root, "data", "events_backfill.json")
    backfill = json.load(open(bpath, encoding="utf-8")).get("events", []) if os.path.exists(bpath) else []
    titled = fill_titles(events + backfill, tdoc.setdefault("items", {}), translate_title or call_title_model, log)
    if titled and not dry:
        _save(tpath, tdoc)
    log(f"event-translate: {len(titled)} titles translated")
    return changed + titled


if __name__ == "__main__":
    run(dry="--dry-run" in sys.argv)
