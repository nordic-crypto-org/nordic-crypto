#!/usr/bin/env python3
"""One illustration per published story, stored in Cloudflare, never in git.

The PNG is an object in the R2 bucket named by CF_R2_STORY_BUCKET
(nordic-crypto-story-images). That bucket is not the private backup
CF_R2_BUCKET. The content Worker serves it at
https://api.nordiccrypto.no/story-images/<id>.png

D1 database nordic-crypto-content (workers/content) holds the row:
story id, object key, style, prompt, kind, size, created time.
The same database holds the style library and the recent-style list
(migration 0003_story_images.sql).

A story that already has kind=ai is not generated again. A headline card
(kind=fallback, written when CF_AI_TOKEN is missing) is replaced once when
the token is present. Pages, og:image, the X post and the video read the
public URL. They do not call the model.

  python3 tools/story_images.py generate --days 7
  python3 tools/story_images.py generate --days 7 --max 40

Exits 0 without writing when D1 or the story-image bucket is not configured.
Does not create the bucket or the database.
"""
from __future__ import annotations

import argparse, datetime as dt, json, os, random, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import x_post_image as painter

# Public origin of the content Worker (workers/content/wrangler.toml).
# The static site and the API point here. The bytes stay in R2.
DEFAULT_ORIGIN = "https://api.nordiccrypto.no"
# Intended bucket. Not created by this script. Not the backup bucket.
DEFAULT_BUCKET = "nordic-crypto-story-images"
BUCKET_ENV = "CF_R2_STORY_BUCKET"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")
WIDTH, HEIGHT = painter.W, painter.H

_INDEX = None


def log(msg):
    print(f"[story-images] {msg}", file=sys.stderr, flush=True)


def origin():
    return (os.environ.get("NC_STORY_IMAGE_ORIGIN") or DEFAULT_ORIGIN).rstrip("/")


def bucket_name():
    """The story-image bucket only. The private backup bucket is never used."""
    name = (os.environ.get(BUCKET_ENV) or "").strip()
    return name


def r2_key(story_id):
    if not ID_RE.match(story_id or ""):
        raise ValueError("story id is not a safe object key")
    return f"story-images/{story_id}.png"


def public_url(story_id, created_at, base=None):
    version = ""
    if created_at:
        from urllib.parse import quote
        version = "?v=" + quote(str(created_at), safe="")
    return f"{(base or origin())}/story-images/{story_id}.png{version}"


def public_record(row, alt=""):
    """Fields the site and /api/v1/ may show. The prompt stays in D1."""
    if not row or not row.get("story_id"):
        return None
    return {
        "url": public_url(row["story_id"], row.get("created_at")),
        "width": int(row.get("width") or WIDTH),
        "height": int(row.get("height") or HEIGHT),
        "alt": alt or "Nordic Crypto",
        "style": row.get("style_id"),
        "kind": "fallback" if row.get("kind") == "fallback" else "original",
    }


def storage_gaps():
    """What is missing before a remote write. Empty when D1 and the bucket name are set."""
    gaps = []
    try:
        import d1_store
        gaps.extend(d1_store.missing_remote())
    except Exception:
        gaps.append("D1")
    if not bucket_name():
        gaps.append(BUCKET_ENV)
    return gaps


def open_store():
    import d1_store
    if d1_store.missing_remote():
        return None
    store = d1_store.open_remote()
    d1_store.apply_schema(store)
    return store


def _styles(store):
    return store.query(
        "SELECT id, prompt, origin, topic, technique, story_id, created_at FROM story_image_styles ORDER BY created_at, id"
    )


def _recent(store):
    import d1_store
    row = d1_store.one(store, "SELECT recent FROM story_image_style_state WHERE id = 1")
    if not row:
        return []
    try:
        data = json.loads(row["recent"] or "[]")
    except json.JSONDecodeError:
        return []
    return [s for s in data if isinstance(s, str)]


def _save_recent(store, recent):
    store.execute(
        "INSERT INTO story_image_style_state (id, recent) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET recent = excluded.recent",
        (json.dumps(list(recent)),),
    )


def _insert_style(store, style, story_id, at):
    store.execute(
        "INSERT INTO story_image_styles (id, prompt, origin, topic, technique, story_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO NOTHING",
        (style["id"], style.get("prompt") or "", style.get("origin") or "topic",
         style.get("topic"), style.get("technique"), story_id, at),
    )


def image_row(store, story_id):
    import d1_store
    return d1_store.one(
        store,
        "SELECT story_id, r2_key, style_id, prompt, kind, width, height, content_type, created_at "
        "FROM story_images WHERE story_id = ?",
        (story_id,),
    )


def _upsert_image(store, row):
    store.execute(
        "INSERT INTO story_images (story_id, r2_key, style_id, prompt, kind, width, height, content_type, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(story_id) DO UPDATE SET r2_key = excluded.r2_key, style_id = excluded.style_id, "
        "prompt = excluded.prompt, kind = excluded.kind, width = excluded.width, height = excluded.height, "
        "content_type = excluded.content_type, created_at = excluded.created_at",
        (row["story_id"], row["r2_key"], row["style_id"], row["prompt"], row["kind"],
         row["width"], row["height"], row["content_type"], row["created_at"]),
    )


def load_rows(store=None):
    """Every stored image row, or [] when D1 is not configured. Does not raise."""
    global _INDEX
    if store is None and _INDEX is not None:
        return _INDEX
    own = store is None
    if store is None:
        if storage_gaps():
            _INDEX = []
            return _INDEX
        try:
            store = open_store()
        except Exception as err:
            log(f"D1 image index unavailable ({type(err).__name__}); pages keep the current image")
            _INDEX = []
            return _INDEX
    try:
        rows = store.query(
            "SELECT story_id, r2_key, style_id, kind, width, height, content_type, created_at FROM story_images"
        )
    except Exception as err:
        log(f"story_images table unavailable ({type(err).__name__}); apply workers/content migrations")
        rows = []
    if own:
        _INDEX = rows
    return rows


def reset_index():
    global _INDEX
    _INDEX = None


def lookup(story_id, alt=""):
    for row in load_rows():
        if row.get("story_id") == story_id:
            return public_record(row, alt)
    return None


def attach(items, rows=None):
    """Set item['story_image'] from D1. Missing rows leave the current picture in place."""
    if rows is None:
        rows = load_rows()
    by_id = {r.get("story_id"): r for r in rows}
    for item in items or []:
        row = by_id.get(item.get("id"))
        if not row:
            item.pop("story_image", None)
            continue
        alt = item.get("title_en") or item.get("title") or "Nordic Crypto"
        item["story_image"] = public_record(row, alt)
    return items


def _parse_published(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def due_stories(items, now, days):
    """Published stories in the window, oldest first. Pending and rejected stay out."""
    cutoff = now - dt.timedelta(days=days)
    chosen = []
    for item in items or []:
        if item.get("status") not in ("published", "owner"):
            continue
        if not item.get("id") or not ID_RE.match(str(item["id"])):
            continue
        if not (item.get("title") or item.get("title_en")):
            continue
        published = _parse_published(item.get("published"))
        if published is None or published < cutoff:
            continue
        chosen.append(item)
    chosen.sort(key=lambda item: (_parse_published(item.get("published")), item["id"]))
    return chosen


def load_news(path=None):
    path = path or os.path.join(ROOT, "data", "news.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("items") or []


def r2_put(local_path, key, *, bucket=None, runner=None):
    """Upload one object. runner(argv) -> (code, text) for tests. Does not create the bucket."""
    name = bucket or bucket_name()
    if not name:
        raise RuntimeError(f"{BUCKET_ENV} is not set")
    cmd = [
        "npx", "--yes", "wrangler", "r2", "object", "put", f"{name}/{key}",
        "--file", local_path, "--content-type", "image/png", "--remote",
    ]
    if runner is not None:
        code, text = runner(cmd)
        if code != 0:
            raise RuntimeError("r2 put failed: " + (text or "")[-300:])
        return
    env = os.environ.copy()
    token = env.get("CLOUDFLARE_API_TOKEN") or ""
    proc = subprocess.run(
        cmd, cwd=os.path.join(ROOT, "workers", "content"),
        capture_output=True, text=True, timeout=180, env=env,
    )
    if proc.returncode != 0:
        detail = ((proc.stderr or "") + "\n" + (proc.stdout or ""))[-400:]
        if token and token in detail:
            detail = detail.replace(token, "[token]")
        raise RuntimeError("r2 put failed: " + detail)


def _needs_image(existing, ai_ready):
    if not existing:
        return True
    if existing.get("kind") == "ai":
        return False
    return bool(ai_ready)


def generate_missing(items, store, *, now, days=7, limit=40, rng=None, generator=None, uploader=None):
    """Generate and store images for due stories that do not already have an AI image.

    Returns a dict of counts. uploader(path, key) stores the PNG. The default
    uploader is the R2 put. generator(prompt) -> bytes, as in x_post_image.
    """
    rng = rng or random.Random()
    styles = _styles(store)
    recent = _recent(store)
    ai_ready = generator is not None or painter.ai_configured()
    made = skipped = failed = upgraded = 0
    todo = due_stories(items, now, days)[: max(0, limit)]
    for item in todo:
        sid = item["id"]
        existing = image_row(store, sid)
        if not _needs_image(existing, ai_ready):
            skipped += 1
            continue
        style = painter.choose_style(styles, recent, item, rng)
        if style.get("id") not in {s.get("id") for s in styles}:
            styles.append(style)
        fd, path = tempfile.mkstemp(prefix="nc-story-", suffix=".png")
        os.close(fd)
        try:
            kind, prompt = painter.render(item, path, style=style, generator=generator)
            if kind == "fallback" and existing and existing.get("kind") == "fallback":
                skipped += 1
                continue
            key = r2_key(sid)
            at = now.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
            (uploader or (lambda p, k: r2_put(p, k)))(path, key)
            _insert_style(store, style, sid, at)
            _upsert_image(store, {
                "story_id": sid, "r2_key": key, "style_id": style["id"], "prompt": prompt,
                "kind": kind, "width": WIDTH, "height": HEIGHT,
                "content_type": "image/png", "created_at": at,
            })
            recent = painter.remember_style(recent, style["id"])
            _save_recent(store, recent)
            if existing and existing.get("kind") == "fallback" and kind == "ai":
                upgraded += 1
            made += 1
            log(f"{sid} {kind} {style['id']}")
        except Exception as err:
            failed += 1
            log(f"{sid} failed: {type(err).__name__}: {err}")
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    reset_index()
    return {
        "considered": len(todo),
        "generated": made,
        "skipped": skipped,
        "failed": failed,
        "upgraded": upgraded,
        "styles": len(styles),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    gen = sub.add_parser("generate", help="store a missing image for each recent published story")
    gen.add_argument("--days", type=int, default=7)
    gen.add_argument("--max", type=int, default=40)
    gen.add_argument("--news", default="")
    a = ap.parse_args(argv)
    gaps = storage_gaps()
    if gaps:
        log("not stored: " + ", ".join(gaps) + " missing. No bucket was created. "
            "Create the R2 bucket nordic-crypto-story-images (free tier), set "
            f"{BUCKET_ENV}, and keep using the existing D1 database nordic-crypto-content. "
            "The private backup bucket CF_R2_BUCKET is not used for these pictures.")
        return 0
    store = open_store()
    now = dt.datetime.now(dt.timezone.utc)
    items = load_news(a.news or None)
    counts = generate_missing(items, store, now=now, days=a.days, limit=a.max)
    log(" ".join(f"{k}={v}" for k, v in counts.items()))
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:
        log(f"fatal: {type(err).__name__}: {err}")
        sys.exit(1)
