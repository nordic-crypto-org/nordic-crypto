#!/usr/bin/env python3
"""YouTube titles and descriptions for Nordic Crypto (English, one template per series).

  build(kind, **fields) -> meta dict (written as build/youtube/<id>/meta.json)
kinds: weekly, sixty, story, regulation, regulation_short, markets, monthly, tool
"""
import datetime as dt
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")
SITE = "https://nordiccrypto.no/"
NFA = "News and information only. Not financial advice."
LOGOS = ("Logos and trademarks belong to their respective owners and are used only to identify the source. "
         "Nordic Crypto is not affiliated with, sponsored by or endorsed by these media outlets.")
FOOTER = ("Nordic Crypto: https://nordiccrypto.no/ · Telegram https://t.me/nordiccryptochat · X https://x.com/nordiccryptobot\n"
          "Contact: jqrgen@nordiccrypto.no")
SHORT_KINDS = {"sixty", "story", "regulation_short", "markets", "tool"}
# (weekday Mon=0 or None for the given date, hour, minute) in Oslo time, from the plan's cadence
SLOTS = {"weekly": (0, 9, 30), "sixty": (0, 12, 0), "story": (None, 12, 0), "regulation": (2, 18, 0),
         "regulation_short": (None, 12, 0), "markets": (4, 16, 0), "monthly": (5, 11, 0), "tool": (None, 12, 0)}


def _d(day):
    return f"{day.day} {day:%b %Y}"


def title(kind, f):
    t = {
        "weekly": lambda: f"Nordic Crypto #{f['number']}: {f['headline']}",
        "sixty": lambda: f"Nordic crypto in 60 seconds: {f['period_label']}",
        "story": lambda: f"{f['country']}: {f['headline']} | Nordic Crypto",
        "regulation": lambda: f"How crypto rules work in {f['country']}: {f['headline']} | Nordic Crypto",
        "regulation_short": lambda: f"{f['headline']} | Nordic Crypto",
        "markets": lambda: f"Bitcoin on Nordic exchanges: snapshot {_d(f['date'])} | Nordic Crypto",
        "monthly": lambda: f"Nordic Crypto: {f['month_label']} in review",
        "tool": lambda: f"{f['headline']} | Nordic Crypto",
    }[kind]()
    return t[:100]


def description(summary, read_more, sources=(), hashtags=("#NordicCrypto", "#Bitcoin"), short=False):
    tags = list(dict.fromkeys(hashtags))
    if short and "#Shorts" not in tags:
        tags.append("#Shorts")
    lines = [summary.strip(), f"Read more: {read_more}"]
    lines += [f"Sources: {o} – {u}" if i == 0 else f"{o} – {u}" for i, (o, u) in enumerate(sources)]
    return "\n".join(lines) + f"\n\n{FOOTER}\n\n{NFA}\n{LOGOS}\n\n" + " ".join(tags[:5])


def publish_at(kind, day, now=None):
    """Planned slot in Oslo as UTC ISO; at least 15 minutes ahead so YouTube accepts it."""
    wd, h, m = SLOTS[kind]
    if wd is not None:
        day = day + dt.timedelta(days=(wd - day.weekday()) % 7)
    slot = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=OSLO)
    now = now or dt.datetime.now(dt.timezone.utc)
    slot = max(slot, now + dt.timedelta(minutes=15))
    return slot.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(kind, *, id, summary, read_more, day, sources=(), hashtags=("#NordicCrypto", "#Bitcoin"),
          tags=("Nordic Crypto", "crypto news"), now=None, **fields):
    short = kind in SHORT_KINDS
    return {
        "id": id, "kind": kind, "short": short,
        "title": title(kind, {**fields, "date": day}),
        "description": description(summary, read_more, sources, hashtags, short),
        "tags": list(tags), "categoryId": "25", "defaultLanguage": "en", "defaultAudioLanguage": "en",
        "tts": True, "containsSyntheticMedia": True,
        "publishAt": publish_at(kind, day, now),
        "video": "video.mp4", "thumbnail": None if short else "thumb.png", "captions": "subs.srt", "playlists": [],
        **{k: v for k, v in fields.items() if k in ("issue",)},
    }
