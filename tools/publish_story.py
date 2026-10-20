#!/usr/bin/env python3
"""Commit one approved own story from queue/approved.json to data/stories/, so the CI deploy publishes it.

  python3 tools/publish_story.py <slug> [--push]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import i18n

def main(slug, push=False):
    st = json.load(open(os.path.join(ROOT, "queue", "approved.json"), encoding="utf-8"))["stories"]
    if slug not in st.get("approve", []): sys.exit(f"{slug}: not in stories.approve")
    summary = dict((st.get("summaries_i18n") or {}).get(slug) or {}, en=(st.get("summaries") or {}).get(slug, ""))
    title = (st.get("titles_i18n") or {}).get(slug) or {}
    missing = [l for l in i18n.ALL_LANGS if not (summary.get(l) or "").strip()] + [l + " title" for l in i18n.ALL_LANGS[1:] if not (title.get(l) or "").strip()]
    if missing: sys.exit(f"{slug}: missing {', '.join(missing)} (set stories.titles_i18n / summaries_i18n)")
    d = os.path.join(ROOT, "data", "stories")
    md = open(st["files"][slug], encoding="utf-8").read().split("\nEditor notes")[0].splitlines()
    if md and md[0].startswith("# "): md[0] = "# Nordic Crypto"
    open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write("\n".join(md).rstrip() + "\n")
    json.dump({"title": title, "summary": summary}, open(os.path.join(d, slug + ".i18n.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ap_path = os.path.join(d, "approved.json")
    ap = json.load(open(ap_path, encoding="utf-8")) if os.path.exists(ap_path) else {"approve": {}}
    ap["approve"][slug] = {"approved_at": (st.get("approved_at") or {}).get(slug), "approved_by": (st.get("approved_by") or {}).get(slug)}
    json.dump(ap, open(ap_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    files = [f"data/stories/{slug}.md", f"data/stories/{slug}.i18n.json", "data/stories/approved.json"]
    subprocess.run(["git", "-C", ROOT, "add", *files], check=True)
    subprocess.run(["git", "-C", ROOT, "commit", "-m", f"Story: {slug}", "--", *files], check=True)
    if push: subprocess.run(["git", "-C", ROOT, "push", "origin", "HEAD:main"], check=True)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--push"]
    if len(args) != 1: sys.exit(__doc__)
    main(args[0], "--push" in sys.argv)
