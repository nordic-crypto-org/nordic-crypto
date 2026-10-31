#!/usr/bin/env python3
"""Post one English digest of new Nordic Crypto stories to X (@nordiccryptobot), at most once per Oslo day.

Runs after every successful "Deploy site" and hourly. Candidates are stories in the live /api/v1/news.json published in
the last 48 h (and not before the first tracked day) that are in no earlier digest. It posts only when every candidate
is fully translated (headline and summary in every site language, the same check as tools/story_translate.py) and its
English page answers 200; otherwise it waits for the next run. From --deadline-hour (Oslo) it posts the ready ones;
the rest go in a later digest when ready and no longer hold one back. Each story: flag, English headline, story link.
Over 280 characters (URLs count 23) it becomes a thread. State: data/x_daily_posted.json, keyed by Oslo date.
Uses the X secrets of tools/x_newsletter.py; without them it logs one line and exits 0.

  python3 tools/x_daily.py [--dry-run] [--feed URL_OR_PATH] [--now ISO] [--deadline-hour 18]
"""
import argparse, datetime as dt, os, sys, time, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headlines, telegram_events as te
import x_newsletter as xn

STATE = os.path.join(xn.ROOT, "data", "x_daily_posted.json")
STORY = "https://nordiccrypto.no/stories/{}/"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
en_title = getattr(te, "en_title", None) or (lambda e: e.get("title_en") or (e.get("title_i18n") or {}).get("en") or e.get("title"))


def log(msg):
    print(f"[x-daily] {msg}", file=sys.stderr, flush=True)


def weight(text):
    """X's weighted length (conservative): URLs 23, Latin and common punctuation 1, everything else 2."""
    n, last = 0, 0
    for m in xn.URL_RE.finditer(text):
        n += _w(text[last:m.start()]) + xn.URL_LEN
        last = m.end()
    return n + _w(text[last:])


def _w(s):
    return sum(1 if c <= 4351 or 8192 <= c <= 8205 or 8208 <= c <= 8223 or 8242 <= c <= 8247 else 2
               for c in map(ord, unicodedata.normalize("NFC", s)))


def header(day):
    return f"📰 New on Nordic Crypto – {day.day} {MONTHS[day.month - 1]} {day.year}"


def item(e):
    flag = te.FLAGS.get((e.get("country") or "").upper(), "•")
    url = STORY.format(e["id"])
    title = " ".join(str(en_title(e)).split())
    while weight(f"{flag} {title}\n{url}") > xn.LIMIT - 40:
        title = title.rsplit(" ", 1)[0].rstrip(",;:–-") + "…" if " " in title else title[:-2] + "…"
    return f"{flag} {title}\n{url}"


def build_posts(stories, day):
    posts, cur = [], header(day)
    for e in stories:
        line = item(e)
        if weight(cur + "\n\n" + line) > xn.LIMIT:
            posts.append(cur); cur = line
        else:
            cur += "\n\n" + line
    return posts + [cur]


def untranslated(e):
    """Site languages still missing the headline or summary, as tools/story_translate.py plans them."""
    have = headlines.title_map(e, {})
    miss = {l for l in headlines.needed_langs(e.get("language")) if not have.get(l)}
    if (e.get("summary") or "").strip():
        miss |= {l for l in headlines.TRANSLATED if not ((e.get("summary_i18n") or {}).get(l) or "").strip()}
    return sorted(miss)


def pick(items, now, state):
    done = {i for v in state.values() for i in v.get("story_ids", [])}
    first = min(state, default=now.astimezone(te.OSLO).date().isoformat())
    start = dt.datetime.fromisoformat(first).replace(tzinfo=te.OSLO)
    since = max(start, now - dt.timedelta(hours=48))
    out = [e for e in items if e.get("id") and en_title(e) and e["id"] not in done
           and (p := te.parse(e.get("published"))) and since <= p <= now]
    return sorted(out, key=lambda e: (te.parse(e["published"]), e["id"]))


def run(feed, state_path, now, *, dry, creds=None, poster=xn.create_post, live=xn.is_live, deadline_hour=18):
    day = now.astimezone(te.OSLO)
    key = day.date().isoformat()
    if feed.get("preview"):
        log("refusing a preview feed"); return 2
    state = xn.load_state(state_path)
    done = state.get(key, {})
    if done.get("complete"):
        log(f"{key} already posted ({done.get('url')}); nothing to do"); return 0
    if done.get("story_ids"):
        byid = {e.get("id"): e for e in feed.get("items") or []}
        stories = [byid[i] for i in done["story_ids"] if i in byid]
    else:
        cands = pick(feed.get("items") or [], now, {k: v for k, v in state.items() if k != key})
        deferred = {i for v in state.values() for i in v.get("deferred", [])}
        stories, waiting = [], {}
        for e in cands:
            miss = untranslated(e)
            if miss or not live(STORY.format(e["id"])):
                waiting[e["id"]] = "untranslated: " + ",".join(miss) if miss else "page not live"
            else:
                stories.append(e)
        why = "; ".join(f"{i} ({w})" for i, w in waiting.items())
        if set(waiting) - deferred and day.hour < deadline_hour:
            log(f"{key}: waiting for {why}"); return 0
        if waiting:
            log(f"{key}: posting without {why}")
    if not stories:
        if waiting and not dry:
            state[key] = {"deferred": sorted(waiting), "complete": False}; xn.save_state(state_path, state)
        log(f"{key}: no new stories ready; nothing to post"); return 0
    posts = build_posts(stories, day)
    if dry:
        for i, p in enumerate(posts, 1):
            print(f"--- {i}/{len(posts)} ({weight(p)}/{xn.LIMIT})\n{p}\n")
        return 0
    if not creds:
        log(f"skipping: missing {', '.join(k for k in xn.ENV if not os.environ.get(k))}"); return 0
    ids = list(done.get("tweet_ids", []))
    entry = {"story_ids": [e["id"] for e in stories], "tweet_ids": ids, "complete": False}
    if not done.get("story_ids") and waiting:
        entry["deferred"] = sorted(waiting)
    for i, text in enumerate(posts):
        if i < len(ids):
            continue
        ids.append(poster(creds, text, reply_to=ids[-1] if ids else None))
        state[key] = entry; xn.save_state(state_path, state)
        log(f"posted {i + 1}/{len(posts)}: {ids[-1]}")
        if i + 1 < len(posts):
            time.sleep(2)
    entry.update(complete=True, posted_at=now.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
                 url=f"https://x.com/nordiccryptobot/status/{ids[0]}")
    state[key] = entry; xn.save_state(state_path, state)
    log(f"done: {entry['url']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the posts; post nothing, keep the state file")
    ap.add_argument("--feed", default=te.NEWS_FEED)
    ap.add_argument("--state", default=STATE)
    ap.add_argument("--now", help="ISO time to run as (testing)")
    ap.add_argument("--deadline-hour", type=int, default=18, help="from this Oslo hour, post the ready stories without waiting")
    a = ap.parse_args(argv)
    now = te.parse(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    creds = tuple(os.environ[k] for k in xn.ENV) if all(os.environ.get(k) for k in xn.ENV) else None
    return run(te.load_feed(a.feed), a.state, now, dry=a.dry_run, creds=creds, deadline_hour=a.deadline_hour)


if __name__ == "__main__":
    sys.exit(main())
