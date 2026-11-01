#!/usr/bin/env python3
"""Post one reply on X as @nordiccryptobot, reusing x_newsletter's client."""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x_newsletter import ENV, create_post, log, x_len


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reply-to", required=True, help="tweet id to reply to")
    ap.add_argument("--text", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not a.reply_to.isdigit():
        sys.exit("--reply-to must be a numeric tweet id")
    text = a.text.strip()
    if not text or x_len(text) > 280:
        sys.exit("text must be 1-280 characters")
    log(f"reply to {a.reply_to}: {text!r}")
    if a.dry_run:
        return
    tid = create_post(tuple(os.environ[k] for k in ENV), text, reply_to=a.reply_to)
    print(f"https://x.com/nordiccryptobot/status/{tid}")


if __name__ == "__main__":
    main()
