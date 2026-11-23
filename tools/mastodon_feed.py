#!/usr/bin/env python3
"""Post new Nordic Crypto events and news digests to Mastodon (@nordiccrypto@mastodon.social), mirroring X.

Same feeds, selection rules, texts and images as tools/x_feed.py: one post per new upcoming event,
one digest per round of new stories with their stored illustrations (or one generated card).
Mastodon allows 500 characters (each URL counts 23), so a long digest continues as replies.
Its own ledger; the first run records what is in the feeds and posts nothing.
Env: MASTODON_TOKEN (scopes write:statuses + write:media), MASTODON_BASE (default https://mastodon.social).
Without the token it logs one line and runs dry.

  python3 tools/mastodon_feed.py --kind events|news --ledger PATH [--dry-run] [--post ID,ID] [--feed URL]
"""
import argparse, datetime as dt, json, mimetypes, os, sys, time, urllib.error, urllib.parse, urllib.request, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import telegram_events as te
import x_feed as xf
import x_newsletter as xn
import x_post_image as xi

BASE = os.environ.get("MASTODON_BASE", "https://mastodon.social").rstrip("/")
UA = "nordic-crypto-mastodon-feed/1 (+https://nordiccrypto.no/)"
LIMIT = 500
MAX_MEDIA = 4


def log(kind, msg):
    print(f"[mastodon-feed {kind}] {msg}", file=sys.stderr, flush=True)


def m_len(text):
    """Length as Mastodon counts it: every URL is 23 characters (same rule as X)."""
    return xn.x_len(text)


def split_digest(text, limit=LIMIT):
    """Split a digest on blank lines into posts of at most `limit`; one block never splits."""
    posts, cur = [], ""
    for block in text.split("\n\n"):
        cand = f"{cur}\n\n{block}" if cur else block
        if cur and m_len(cand) > limit:
            posts.append(cur)
            cur = block
        else:
            cur = cand
    if cur:
        posts.append(cur)
    return [p if m_len(p) <= limit else p[: limit - 1] + "…" for p in posts]


def fit(text, limit=LIMIT):
    """Shorten the first line (the title) until an event post fits."""
    if m_len(text) <= limit:
        return text
    first, _, rest = text.partition("\n")
    room = max(10, len(first) - (m_len(text) - limit) - 1)
    return first[:room].rstrip() + "…\n" + rest


# ---------------------------------------------------------------- Mastodon API
def _call(token, method, path, *, data=None, headers=None, base=BASE):
    req = urllib.request.Request(base + path, method=method, data=data,
                                 headers={"Authorization": f"Bearer {token}", "User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def upload_image(token, path, *, base=BASE, sleep=time.sleep):
    """POST /api/v2/media; wait until processed so the status can use it. Returns the media id."""
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        blob = fh.read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + blob + f"\r\n--{boundary}--\r\n".encode()
    media = _call(token, "POST", "/api/v2/media", data=body, base=base,
                  headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    for _ in range(15):
        if media.get("url"):
            break
        sleep(2)
        media = _call(token, "GET", f"/api/v1/media/{media['id']}", base=base)
    return media["id"]


def create_status(token, text, media_ids=None, reply_to=None, *, base=BASE):
    form = [("status", text), ("visibility", "public"), ("language", "en")]
    form += [("media_ids[]", m) for m in media_ids or []]
    if reply_to:
        form.append(("in_reply_to_id", reply_to))
    st = _call(token, "POST", "/api/v1/statuses", data=urllib.parse.urlencode(form).encode(), base=base,
               headers={"Content-Type": "application/x-www-form-urlencoded", "Idempotency-Key": uuid.uuid4().hex})
    return st["id"], st.get("url")


# ---------------------------------------------------------------- run
def plan(feed, seen, *, now, kind, force, max_posts, max_age_days, settle_minutes, log_fn):
    """(ids, text, lead) per post, using x_feed's selection rules. None means wait."""
    events = (feed.get("items") if kind == "news" else feed.get("events")) or []
    byid = {e.get("id"): e for e in events}
    for i in force:
        if i not in byid:
            log_fn(f"{i} is not in the feed")
    if kind == "news":
        updated = te.parse(feed.get("updated"))
        if not force and updated and now - updated < dt.timedelta(minutes=settle_minutes):
            log_fn(f"feed updated {updated.isoformat()}, waiting for the publish round to settle")
            return None, byid
        fresh = [e for e in te.fresh_news(events, now, max_age_days) if e["id"] not in seen]
        forced = [byid[i] for i in dict.fromkeys(force) if i in byid]
        todo = te.fresh_news(forced, now, 36500) + [e for e in fresh if e["id"] not in force]
        todo.sort(key=lambda e: (te.parse(e["published"]), e["id"]))
        return ([([e["id"] for e in todo], xf.news_digest(todo, now), xf.lead_item(todo, "news"))] if todo else []), byid
    todo = [e for e in te.postable(events, now) if e["id"] not in seen]
    have = {e["id"] for e in todo}
    extra = [byid[i] for i in dict.fromkeys(force) if byid.get(i, {}).get("title") and i not in have]
    return [([e["id"]], fit(xf.event_text(e)), e) for e in (extra + todo)[:max_posts]], byid


def media_for(token, kind, ids, byid, lead, styles, *, uploader, fetcher, image_renderer, log_fn):
    """Stored story pictures (up to four), else one generated card. Returns (media_ids, style_id)."""
    pictures = xf.pictures_for(ids, byid) if kind == "news" else []
    if xf.story_image_urls(pictures):
        return xf.attach_story_images(token, pictures, uploader=uploader, fetcher=fetcher, log_fn=log_fn)[:MAX_MEDIA], None
    path, style_id = xf.make_image(lead, kind, styles, image_renderer=image_renderer)
    if not path:
        return [], None
    try:
        return [uploader(token, path)], style_id
    except Exception as err:
        log_fn(f"image upload failed ({type(err).__name__}: {err}); posting without media")
        return [], None
    finally:
        xf._drop(path)


def run(feed, ledger_path, *, now, token, max_posts, dry, kind="events", force=(), max_age_days=7,
        settle_minutes=10, poster=create_status, uploader=upload_image, image_fetcher=None,
        image_renderer=None, log_fn=None, pause=1.0):
    log_fn = log_fn or (lambda m: log(kind, m))
    if feed.get("preview"):
        log_fn("refusing a preview feed")
        return 2
    have = os.path.exists(ledger_path)
    ledger = xn.load_state(ledger_path) if have else {}
    seen = set(ledger.get("posted") or [])
    styles = list(ledger.get("styles") or [])
    force = [i for i in force if i]
    if not have:
        items = (feed.get("items") if kind == "news" else feed.get("events")) or []
        seen = {e["id"] for e in items if e.get("id")}
        if not dry:
            xf.save_ledger(ledger_path, sorted(seen), styles)
        log_fn(f"no ledger yet; recorded {len(seen)} current {kind}" + ("" if force else ", posted nothing")
               + (" (dry run, not saved)" if dry else ""))
        if not force:
            return 0
    msgs, byid = plan(feed, seen, now=now, kind=kind, force=force, max_posts=max_posts,
                      max_age_days=max_age_days, settle_minutes=settle_minutes, log_fn=log_fn)
    if msgs is None:
        return 0
    if not msgs:
        log_fn("nothing new")
        return 0
    posted = 0
    for ids, text, lead in msgs:
        parts = split_digest(text) if kind == "news" else [text]
        if dry or not token:
            why = "dry run" if dry else "missing MASTODON_TOKEN"
            log_fn(f"--- would post {', '.join(ids)} ({why}, {len(parts)} post(s)):\n" + "\n---\n".join(parts))
            continue
        media, style_id = media_for(token, kind, ids, byid, lead, styles, uploader=uploader,
                                    fetcher=image_fetcher or xf._download_image,
                                    image_renderer=image_renderer, log_fn=log_fn)
        reply_to, first_url = None, None
        for n, part in enumerate(parts):
            try:
                sid, url = poster(token, part, media_ids=media if n == 0 else None, reply_to=reply_to)
            except Exception as err:
                detail = f"HTTP {err.code}" if isinstance(err, urllib.error.HTTPError) else type(err).__name__
                hint = " (does the token have write:statuses and write:media?)" if detail in ("HTTP 401", "HTTP 403") else ""
                log_fn(f"send failed for {', '.join(ids)} part {n + 1}/{len(parts)}: {detail}: {err}{hint}")
                if n == 0:
                    return 1
                break  # the head is out; record the round so it is not posted twice
            reply_to, first_url = sid, first_url or url
        seen.update(ids)
        posted += len(ids)
        if style_id:
            styles = xi.remember_style(styles, style_id)
        xf.save_ledger(ledger_path, sorted(seen), styles)
        log_fn(f"posted {', '.join(ids)}: {first_url} ({len(parts)} post(s), {len(media)} image(s))")
        time.sleep(pause)
    log_fn(f"{posted} posted" + (" (dry run)" if dry or not token else ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--kind", choices=("events", "news"), default="events")
    ap.add_argument("--feed")
    ap.add_argument("--post", default="", help="comma-separated ids to post now (backfill)")
    ap.add_argument("--max-age-days", type=int, default=7)
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    token = os.environ.get("MASTODON_TOKEN") or None
    dry = a.dry_run
    if not token and not dry:
        log(a.kind, "skipping: missing MASTODON_TOKEN; dry run")
        dry = True
    feed = a.feed or (te.NEWS_FEED if a.kind == "news" else te.FEED)
    force = [i.strip() for i in a.post.replace(" ", ",").split(",") if i.strip()]
    return run(te.load_feed(feed), a.ledger, now=dt.datetime.now(dt.timezone.utc), token=token,
               max_posts=max(1, a.max), dry=dry, kind=a.kind, force=force, max_age_days=a.max_age_days)


if __name__ == "__main__":
    sys.exit(main())
