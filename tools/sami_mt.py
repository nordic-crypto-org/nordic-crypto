#!/usr/bin/env python3
"""Northern Sami (se) machine translation for the site pipeline.

Workers AI models do not write usable Northern Sami, so `se` goes to the University of Tartu's public
translation API (TartuNLP, https://api.tartunlp.ai/translation/v2; no key). Source: English, or Norwegian / Finnish.
Placeholders ({n}, $x), HTML tags and entities are masked and must come back unchanged; a reply that loses one,
drops "Nordic Crypto", or reads as Norwegian/Swedish/English is returned as None (the caller leaves that text missing).
"""
import json, re, sys, time, urllib.request

API = "https://api.tartunlp.ai/translation/v2"
SRC = {"en": "eng", "nb": "nor", "nn": "nor", "fi": "fin"}
BRAND = "Nordic Crypto"
_TOKEN = re.compile(r"\{[^{}]*\}|\$[A-Za-z_]+|&#?\w+;|https?://[^\s\"<>)]+")
_TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>")
_VOID = {"br", "img", "hr", "wbr", "input", "meta", "link", "source"}
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9ÆØÅÄÖ\"“])")
_FOREIGN = re.compile(r"\b(og|ikke|eller|med|til|som|och|är|inte|för|the|and|of|with|you|your|is|are|this|velkommen)\b", re.I)


def mask(text):
    toks, ids = [], []
    def tok(m):
        toks.append(m.group(0)); return f"⟦{len(toks) - 1}⟧"
    out = _TOKEN.sub(tok, text)
    stack, opened, parts, pos = [], [], [], 0
    for m in _TAG.finditer(out):
        parts.append(out[pos:m.start()]); pos = m.end()
        close, name = m.group(1), m.group(2).lower()
        if close and stack and stack[-1][0] == name:
            parts.append("</g>"); stack.pop()
        elif not close and not m.group(4) and name not in _VOID:
            opened.append(m.group(0)); stack.append((name, len(opened) - 1)); parts.append(f'<g id="{len(opened) - 1}">')
        else:
            toks.append(m.group(0)); parts.append(f"⟦{len(toks) - 1}⟧")
    parts.append(out[pos:])
    if stack:
        return None
    return "".join(parts), toks, opened


def unmask(text, toks, opened):
    names = [re.match(r"<([a-zA-Z][\w-]*)", o).group(1) for o in opened]
    seen, stack = [], []
    def g(m):
        if m.group(1):
            return f"</{names[stack.pop()]}>" if stack else m.group(0)
        i = int(m.group(2)); seen.append(i); stack.append(i); return opened[i]
    text = re.sub(r'<(/)g>|<g id="(\d+)">', g, text)
    if sorted(seen) != list(range(len(opened))) or stack:
        return None
    for i, t in enumerate(toks):
        if text.count(f"⟦{i}⟧") != 1:
            return None
        text = text.replace(f"⟦{i}⟧", t)
    return None if "⟦" in text or "<g" in text else text


def _call(texts, src):
    body = json.dumps({"text": texts, "src": SRC[src], "tgt": "sme", "domain": "general"}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={"Content-Type": "application/json",
                                 "User-Agent": "NordicCrypto/1.0 (+https://nordiccrypto.no/)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)["result"]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def check(src, out):
    if not out or not out.strip():
        return False
    if BRAND in src and BRAND not in out:
        return False
    plain = re.sub(r"<[^>]+>|\{[^}]*\}", " ", out)
    copied = {s.strip() for s in re.split(r"(?<=[.!?])\s+", src) if len(s.split()) >= 5} & {s.strip() for s in re.split(r"(?<=[.!?])\s+", out)}
    return not copied and len(_FOREIGN.findall(plain)) <= max(0, len(plain.split()) // 25)


def translate(texts, src="en", batch=16, alt=None, alt_src="nb"):
    """List of source texts -> list of Northern Sami texts (None where the reply failed a check).
    alt: the same texts in alt_src, tried where the first reply failed."""
    res = _translate(texts, src, batch)
    for i in [i for i, r in enumerate(res) if r is None and "<" not in (texts[i] or "")]:
        parts = [p for p in _SENT.split(texts[i].strip()) if p]
        if len(parts) > 1:
            got = _translate(parts, src, batch)
            if all(g is not None for g in got):
                res[i] = " ".join(got) if check(texts[i], " ".join(got)) else None
    redo = [i for i, r in enumerate(res) if r is None and alt and (alt[i] or "").strip()]
    if redo:
        for i, r in zip(redo, _translate([alt[i] for i in redo], alt_src, batch)):
            res[i] = r if r is not None and check(texts[i], r) else None
    return res


def _translate(texts, src, batch):
    res = [None] * len(texts)
    jobs = []
    for i, t in enumerate(texts):
        if not (t or "").strip():
            continue
        m = mask(t)
        if m:
            jobs.append((i, m))
    for k in range(0, len(jobs), batch):
        chunk = jobs[k:k + batch]
        try:
            got = _call([m[0] for _, m in chunk], src)
        except Exception as e:
            print(f"sami-mt: {type(e).__name__}", file=sys.stderr); continue
        inner = {}
        for n, ((i, m), out) in enumerate(zip(chunk, got)):
            for g in re.finditer(r'<g id="(\d+)">([^<>]*)</g>', out or ""):
                if g.group(2) in m[0] and len(re.findall(r"\b[a-z]{2,}\b", g.group(2))) >= 2:
                    inner.setdefault(g.group(2), None)
        if inner:
            keys = list(inner)
            try:
                for key, val in zip(keys, _call(keys, src)):
                    if val and not _TOKEN.search(key):
                        inner[key] = val.strip().rstrip(".") if not key.endswith(".") else val.strip()
            except Exception:
                pass
            got = [re.sub(r'(<g id="\d+">)([^<>]*)(</g>)', lambda g: g.group(1) + (inner.get(g.group(2)) or g.group(2)) + g.group(3), o or "")
                   for o in got]
        for (i, m), out in zip(chunk, got):
            out = unmask((out or "").strip(), m[1], m[2])
            if out is not None and texts[i] != texts[i].strip():
                out = texts[i][:len(texts[i]) - len(texts[i].lstrip())] + out + texts[i][len(texts[i].rstrip()):]
            res[i] = out if out is not None and check(texts[i], out) else None
    return res


if __name__ == "__main__":
    print(json.dumps(translate([l.rstrip("\n") for l in sys.stdin]), ensure_ascii=False, indent=1))
