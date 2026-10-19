#!/usr/bin/env python3
"""Every published newsletter issue in every site language.

Fills what is missing next to the English issue in newsletter/published/<id>/:
  issue.<lang>.html                    the issue body (block by block, tags and links kept exactly)
  issues.json title_i18n/subtitle_i18n  title and subtitle

Existing translations are never replaced. Model: Workers AI, as tools/story_translate.py (CF_AI_TOKEN and
CF_ACCOUNT_ID, or CLOUDFLARE_*). Northern Sami (se) goes to tools/sami_mt.py (TartuNLP) when that module is
present. Without credentials the tool prints one line and exits 0.

  python3 tools/issue_translate.py [--issue 003] [--lang de] [--dry-run]
"""
import argparse, concurrent.futures as cf, json, os, re, sys, threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import i18n  # noqa: E402
from tools import story_translate as st  # noqa: E402

PUB = os.path.join(ROOT, "newsletter", "published")
BLOCK = re.compile(r"(<(p|li|h[1-4]|td|th)(?:\s[^>]*)?>)(.*?)(</\2>)", re.S)
TAG = re.compile(r"<[^>]+>")
URL = re.compile(r"https?://\S+")
BATCH = 24
KEEP = {"The Nordic Crypto team"}   # sign-off stays English, as in the Nordic issues
MAX_MISS = 0.1   # more failed blocks than this and the language is left out (the page shows English)
NAMES = dict(st.NAMES, se="Northern Sami")
PROMPT = (
    "You translate a newsletter from Nordic Crypto, a news site about Bitcoin, blockchain and crypto in the Nordic "
    "countries, from English into {name}. Plain, neutral news style, the same facts, nothing added, nothing left out. "
    "Each value is an HTML fragment: keep every tag and attribute exactly as it is and in the same place, translate only "
    "the text between tags. Keep URLs, numbers, amounts and dates exact. Keep names of people, companies, outlets, "
    "authorities and products as they are. Keep \"Nordic Crypto\" exactly as written, in Latin letters. Do not mention "
    "AI or translation. Return JSON only: an object with exactly the same keys, each value translated."
)
_lock = threading.Lock()


def plain(s):
    return URL.sub(" ", TAG.sub(" ", s)).strip()


def needs_text(inner):
    return bool(re.search(r"[^\W\d_]", plain(inner))) and plain(inner) not in KEEP


def segments(html):
    """[(key, inner_html)] for every block with text to translate."""
    return [(str(n), m.group(3)) for n, m in enumerate(BLOCK.finditer(html)) if needs_text(m.group(3))]


def rebuild(html, done):
    n = [-1]
    def sub(m):
        n[0] += 1
        return m.group(1) + done.get(str(n[0]), m.group(3)) + m.group(4)
    return BLOCK.sub(sub, html)


def ok(lang, src, out):
    if not isinstance(out, str) or not out.strip():
        return False
    if sorted(TAG.findall(src)) != sorted(TAG.findall(out)):
        return False
    if sorted(URL.findall(plain_urls(src))) != sorted(URL.findall(plain_urls(out))):
        return False
    s, o = plain(src), plain(out)
    if len(s) < 4:
        return True
    return st.valid(lang, "headline" if len(s) < 80 else "summary", o, s) == ""


def plain_urls(s):
    return TAG.sub(" ", s)


def model_batch(lang, items, translate):
    if lang == "se":
        from tools import sami_mt   # TartuNLP; present once Northern Sami is a site language
        outs = sami_mt.translate([v for _, v in items], src="en")
        return {k: o for (k, _), o in zip(items, outs) if o}
    res = translate(PROMPT.format(name=NAMES.get(lang, lang)), json.dumps(dict(items), ensure_ascii=False))
    return {str(k): st.tidy(v) if "<" not in str(v) else str(v).replace("\u2011", "-").replace("\u2010", "-").strip() for k, v in (res or {}).items()}


def translate_lang(lang, items, translate, log):
    """{key: text} for the items that passed the checks; each batch is tried twice."""
    done = {}
    for i in range(0, len(items), BATCH):
        part = items[i:i + BATCH]
        for _ in range(2):
            todo = [(k, v) for k, v in part if k not in done]
            if not todo:
                break
            try:
                got = model_batch(lang, todo, translate)
            except Exception as ex:
                log(f"issue_translate: {lang} batch failed: {str(ex)[:120]}")
                continue
            for k, v in todo:
                if ok(lang, v, got.get(k)):
                    done[k] = got[k]
    return done


def save_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def run(issue=None, langs=None, dry=False, translate=None, log=print, pub=PUB, workers=6):
    meta_path = os.path.join(pub, "issues.json")
    meta = st.load(meta_path, {"issues": []})
    targets = [l for l in (langs or i18n.ALL_LANGS) if l != "en"]
    if "se" in targets:
        try:
            from tools import sami_mt  # noqa: F401
        except ImportError:
            targets.remove("se")
    if translate is None and not dry:
        account, token = st._endpoint()
        if not (account and token):
            log("issue_translate: no CF_AI_TOKEN/CF_ACCOUNT_ID, nothing translated")
            return 0
        translate = st.call_model
    jobs = []
    for iss in meta.get("issues", []):
        if issue and str(iss.get("id")) != str(issue):
            continue
        base = os.path.join(pub, str(iss["id"]), "issue.html")
        if (iss.get("lang") or "en") != "en" or not os.path.exists(base):
            continue
        for lang in targets:
            body = not os.path.exists(os.path.join(pub, str(iss["id"]), f"issue.{lang}.html"))
            head = [k for k in ("title", "subtitle") if iss.get(k) and not (iss.get(k + "_i18n") or {}).get(lang)]
            if body or head:
                jobs.append((iss, lang, body, head))
    if dry:
        for iss, lang, body, head in jobs:
            log(f"issue_translate: {iss['id']} {lang} missing {'body ' if body else ''}{' '.join(head)}")
        return len(jobs)

    def one(job):
        iss, lang, body, head = job
        html = open(os.path.join(pub, str(iss["id"]), "issue.html"), encoding="utf-8").read()
        segs = segments(html) if body else []
        items = segs + [(k, iss[k]) for k in head]
        done = translate_lang(lang, items, translate, log)
        miss = [k for k, _ in segs if k not in done]
        with _lock:
            if body and segs and len(miss) <= MAX_MISS * len(segs):
                save_text(os.path.join(pub, str(iss["id"]), f"issue.{lang}.html"), rebuild(html, done))
            for k in head:
                if k in done:
                    iss.setdefault(k + "_i18n", {})[lang] = done[k]
            save_meta(meta_path, meta)
            log(f"issue_translate: {iss['id']} {lang}: {len(segs) - len(miss)}/{len(segs)} blocks, "
                f"{sum(k in done for k in head)}/{len(head)} headers" + (" (body left out)" if body and segs and len(miss) > MAX_MISS * len(segs) else ""))
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, jobs))
    return len(jobs)


def save_meta(path, meta):
    order = [l for l in i18n.ALL_LANGS if l != "en"] + ["se"]
    for iss in meta.get("issues", []):
        for k in ("title_i18n", "subtitle_i18n"):
            if iss.get(k):
                iss[k] = {l: iss[k][l] for l in sorted(iss[k], key=lambda l: order.index(l) if l in order else 99)}
    st.save(path, meta)


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--issue"); a.add_argument("--lang", action="append"); a.add_argument("--dry-run", action="store_true")
    o = a.parse_args()
    run(o.issue, o.lang, o.dry_run)
