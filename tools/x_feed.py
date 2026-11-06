#!/usr/bin/env python3
"""Post new Nordic Crypto events and news digests to X (@nordiccryptobot), mirroring Telegram.

Same selection rules as tools/telegram_events.py (live feeds, ledger, settle window, --post backfill).
Plain-text posts: one digest for new stories (English headlines, nordiccrypto.no links, Source: name),
one post per new upcoming event (title, date/time, venue/address, organiser, Nordic Crypto page).

A news digest attaches the illustrations already stored for those stories (up to four).
When none of the stories has a stored picture, the post falls back to one image generated
on the fly (tools/x_post_image.py): a rotating style, «Nordic Crypto» top-right, and a
headline card when Workers AI credentials are missing. Events have no stored picture,
so they always use that fallback. Uses the X OAuth secrets of tools/x_newsletter.py;
without them it logs one line and exits 0 (dry).

  python3 tools/x_feed.py --kind events|news --ledger PATH [--dry-run] [--post ID,ID] [--feed URL]
"""
import argparse, datetime as dt, os, sys, tempfile, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import telegram_events as te
import x_newsletter as xn
import x_post_image as xi

UA = "nordic-crypto-x-feed/1 (+https://nordiccrypto.no/)"
MAX_URLS = xn.MAX_URLS


def log(kind, msg):
    print(f"[x-feed {kind}] {msg}", file=sys.stderr, flush=True)


def event_text(e):
    """Plain-text event post. Only public-feed facts; no phone numbers."""
    place = e.get("place") or ""
    city = e.get("city") or ""
    if city and city not in place:
        place = f"{place}, {city}" if place else city
    if not place and e.get("online"):
        place = "Online"
    flag = te.FLAGS.get((e.get("country") or "").upper(), "")
    lines = [f"📅 New event: {e['title']}", f"🗓 {te.when(e)}"]
    if place:
        lines.append(f"📍 {flag + ' ' if flag else ''}{place}")
    if e.get("organiser"):
        lines.append(f"👥 {e['organiser']}")
    link = e.get("html_url") or (f"{te.SITE}/calendar/{e['id']}/" if e.get("id") else None)
    if link and str(link).startswith(te.SITE):
        lines.append(link)
    elif link:
        lines.append(f"{te.SITE}/calendar/{e['id']}/" if e.get("id") else link)
    return "\n".join(lines)


def news_digest(items, now):
    """One plain-text digest: header, then flag + English title – Source: name + story URL."""
    head = f"📰 New stories on Nordic Crypto – {now.astimezone(te.OSLO).strftime('%-d.%-m.%Y')}"
    blocks, urls = [head], 0
    for e in items:
        flag = te.FLAGS.get((e.get("country") or "").upper(), "•")
        title = " ".join(str(te.en_title(e) or "").split())
        link = te.en_link(e) or f"{te.SITE}/stories/{e['id']}/"
        line = f"{flag} {title}"
        if e.get("source_name"):
            line += f" – Source: {e['source_name']}"
        if urls >= MAX_URLS:
            blocks.append(line)
        else:
            blocks.append(f"{line}\n{link}")
            urls += 1
    return "\n\n".join(blocks)


def save_ledger(path, posted_ids, styles):
    """Write posted ids and recent on-the-fly style ids together."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    import json
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"posted": list(posted_ids), "styles": list(styles)}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def lead_item(items, kind):
    """Newest story for a fallback image; the single event otherwise."""
    if not items:
        return None
    if kind == "news":
        return max(items, key=lambda e: (te.parse(e.get("published")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc), e["id"]))
    return items[0]


def pictures_for(ids, byid):
    return [byid[i] for i in ids if byid.get(i)]


def story_image_urls(items, limit=4):
    """Public illustration URLs already stored for these stories. At most four."""
    urls = []
    for item in items or []:
        image = item.get("image") if isinstance(item, dict) else None
        url = image.get("url") if isinstance(image, dict) else None
        if not url or not str(url).startswith("https://") or url in urls:
            continue
        urls.append(str(url))
        if len(urls) >= limit:
            break
    return urls


def _download_image(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    if not data or len(data) < 32:
        return None
    fd, path = tempfile.mkstemp(prefix="nc-x-img-", suffix=".png")
    os.close(fd)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def attach_story_images(creds, items, *, uploader, fetcher, log_fn):
    """Upload pictures that are already stored. A failed download does not generate a new one."""
    ids = []
    for url in story_image_urls(items):
        path = None
        try:
            path = fetcher(url)
            if not path:
                continue
            ids.append(uploader(creds, path))
        except Exception as err:
            log_fn(f"stored image skipped ({type(err).__name__})")
        finally:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
    return ids


def make_image(item, kind, styles, *, image_renderer=None):
    """On-the-fly card for an item that has no stored picture. Returns (path, style_id)."""
    if not item:
        return None, None
    renderer = image_renderer or xi.render
    fd, path = tempfile.mkstemp(prefix="nc-x-", suffix=".png")
    os.close(fd)
    try:
        style_id, path = renderer(item, path, kind=kind, recent_styles=styles)
        return path, style_id
    except Exception as err:
        log(kind, f"image render failed: {type(err).__name__}: {err}")
        try:
            os.unlink(path)
        except OSError:
            pass
        return None, None


def _drop(path):
    if path and os.path.exists(path) and not os.environ.get("NC_X_KEEP_IMAGES"):
        try:
            os.unlink(path)
        except OSError:
            pass


def post_x(creds, text, poster=xn.create_post, media_id=None, media_ids=None):
    if xn.x_len(text) > xn.LONG_LIMIT:
        return None, f"text exceeds X long-post limit ({xn.x_len(text)}/{xn.LONG_LIMIT})"
    ids = [i for i in (media_ids or []) if i]
    if media_id and media_id not in ids:
        ids.insert(0, media_id)
    attempts = []
    if len(ids) == 1:
        attempts.append({"media_id": ids[0]})
        attempts.append({"media_ids": ids})
    elif ids:
        attempts.append({"media_ids": ids})
        attempts.append({"media_id": ids[0]})
    attempts.append({})
    last = "poster rejected the call"
    for kw in attempts:
        try:
            return (poster(creds, text, **kw) if kw else poster(creds, text)), ""
        except TypeError as err:
            last = str(err)
            continue
        except Exception as err:
            return None, f"{type(err).__name__}: {err}"
    return None, last


def run(feed, ledger_path, *, now, creds, max_posts, dry, kind="events", force=(), max_age_days=7,
        settle_minutes=10, poster=xn.create_post, log_fn=None, uploader=None, image_renderer=None,
        image_uploader=None, image_fetcher=None):
    log_fn = log_fn or (lambda m: log(kind, m))
    if feed.get("preview"):
        log_fn("refusing a preview feed")
        return 2
    events = (feed.get("items") if kind == "news" else feed.get("events")) or []
    have = os.path.exists(ledger_path)
    ledger = xn.load_state(ledger_path) if have else {"posted": []}
    if "posted" not in ledger:
        ledger = {"posted": list(ledger.get("posted") or []), **{k: v for k, v in ledger.items() if k != "posted"}}
    seen = set(ledger.get("posted") or [])
    styles = list(ledger.get("styles") or [])
    force = [i for i in force if i]
    if not have:
        ids = sorted({e["id"] for e in events if e.get("id")})
        seen = set(ids)
        if not dry:
            save_ledger(ledger_path, ids, styles)
        log_fn(f"no ledger yet; recorded {len(ids)} current {kind}"
               + ("" if force else ", posted nothing")
               + (" (dry run, not saved)" if dry else ""))
        if not force:
            return 0
    byid = {e.get("id"): e for e in events}
    for i in force:
        if i not in byid:
            log_fn(f"{i} is not in the feed")
    msgs = []
    if kind == "news":
        updated = te.parse(feed.get("updated"))
        if not force and updated and now - updated < dt.timedelta(minutes=settle_minutes):
            log_fn(f"feed updated {updated.isoformat()}, waiting for the publish round to settle")
            return 0
        fresh = [e for e in te.fresh_news(events, now, max_age_days) if e["id"] not in seen]
        forced = [byid[i] for i in dict.fromkeys(force) if i in byid]
        todo = te.fresh_news(forced, now, 36500) + [e for e in fresh if e["id"] not in force]
        todo.sort(key=lambda e: (te.parse(e["published"]), e["id"]))
        if todo:
            msgs = [([e["id"] for e in todo], news_digest(todo, now), lead_item(todo, "news"))]
    else:
        todo = [e for e in te.postable(events, now) if e["id"] not in seen]
        forced = [byid[i] for i in dict.fromkeys(force) if i in byid and i not in {e["id"] for e in todo}]
        extra = []
        for i in dict.fromkeys(force):
            e = byid.get(i)
            if not e or not e.get("title"):
                continue
            if e["id"] in {x["id"] for x in todo}:
                continue
            extra.append(e)
        todo = extra + todo
        msgs = [([e["id"]], event_text(e), e) for e in todo[:max_posts]]
    if not msgs:
        log_fn("nothing new")
        return 0
    posted = 0
    upload = uploader or image_uploader or xn.upload_image
    fetcher = image_fetcher or _download_image
    for ids, text, lead in msgs:
        pictures = pictures_for(ids, byid) if kind == "news" else []
        stored = story_image_urls(pictures)
        style_id = None
        if dry or not creds:
            why = "dry run" if dry else f"missing {', '.join(k for k in xn.ENV if not os.environ.get(k))}"
            if stored:
                note = f" + {len(stored)} stored image(s)"
            else:
                img_path, style_id = make_image(lead, "news" if kind == "news" else "events", styles,
                                               image_renderer=image_renderer)
                note = f" + image:{style_id or 'none'}" + (f" ({img_path})" if img_path else "")
                if img_path and style_id:
                    styles = xi.remember_style(styles, style_id)
                _drop(img_path)
            log_fn(f"--- would post {', '.join(ids)} ({why}){note}:\n{text}")
            continue
        media_id = None
        media_ids = None
        if stored:
            media_ids = attach_story_images(creds, pictures, uploader=upload, fetcher=fetcher, log_fn=log_fn) or None
        else:
            img_path, style_id = make_image(lead, "news" if kind == "news" else "events", styles,
                                           image_renderer=image_renderer)
            if img_path:
                try:
                    media_id = upload(creds, img_path)
                except Exception as err:
                    log_fn(f"image upload failed ({type(err).__name__}: {err}); posting without media")
                    media_id = None
                finally:
                    _drop(img_path)
        tid, err = post_x(creds, text, poster=poster, media_id=media_id, media_ids=media_ids)
        if not tid:
            log_fn(f"send failed for {', '.join(ids)}: {err}")
            return 1
        seen.update(ids)
        posted += len(ids)
        if style_id:
            styles = xi.remember_style(styles, style_id)
        save_ledger(ledger_path, sorted(seen), styles)
        how = f"image {style_id}" if style_id else (f"{len(stored)} stored image(s)" if stored else "")
        log_fn(f"posted {', '.join(ids)}: https://x.com/nordiccryptobot/status/{tid}"
               + (f" ({how})" if how else ""))
        time.sleep(1)
    left = 0 if (dry or not creds) else (len(todo) - posted if kind == "events" else 0)
    log_fn(f"{posted} posted, {left} left for the next run"
           + (" (dry run)" if dry or not creds else ""))
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
    creds = tuple(os.environ[k] for k in xn.ENV) if all(os.environ.get(k) for k in xn.ENV) else None
    dry = a.dry_run
    if not creds and not dry:
        log(a.kind, f"skipping: missing {', '.join(k for k in xn.ENV if not os.environ.get(k))}; dry run")
        dry = True
    feed = a.feed or (te.NEWS_FEED if a.kind == "news" else te.FEED)
    force = [i.strip() for i in a.post.replace(" ", ",").split(",") if i.strip()]
    return run(te.load_feed(feed), a.ledger, now=dt.datetime.now(dt.timezone.utc), creds=creds,
               max_posts=max(1, a.max), dry=dry, kind=a.kind, force=force, max_age_days=a.max_age_days)


if __name__ == "__main__":
    sys.exit(main())
