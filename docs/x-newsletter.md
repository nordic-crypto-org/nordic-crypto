# Newsletter → X long post (@nordiccryptobot)

`tools/x_newsletter.py` posts each new weekly Nordic Crypto issue to X once, as **one long post** (X Premium)
from **@nordiccryptobot** only. The token is checked with `GET /2/users/me`. @jQrgensn, or any other account, is
refused and nothing is posted. Never a thread: if X rejects the post, the run fails and nothing is posted.

```
Nordic Crypto #N: <headline>
https://nordiccrypto.no/newsletter/<id>/

<story headline>
https://nordiccrypto.no/stories/<story id>/
…
```

Every story links to its page on nordiccrypto.no, never the original source. Story ids come from `data/news.json`
and `archive/articles.json`, matched on the source URL in `issue.html`. There is no silent link cap: a headline is
not listed without its page, and a post that is over the long-post limit (25,000, URLs counted as 23) fails instead
of dropping stories. `MAX_URLS` remains only for the news digest in `tools/x_feed.py`.

The post attaches one generated image of the issue. The style is a new row in the D1 style library (cyanotype,
wax-resist, copperplate or marbled paper before any technique already stored). «Nordic Crypto» is drawn in the
top-right. Outlet names are scrubbed from the prompt. No outlet logo is drawn. The PNG is an object in the R2 bucket
`nordic-crypto-story-images` and a row in D1 (`story_id` `newsletter-<id>`). It is not committed. A headline card is
not posted: without a Workers AI picture the run fails and `data/x_posted.json` is left unchanged, so the next run
can try again.

X allows one video or up to four images on a post, not both. The newsreel is downloaded and checked against
`video.sha256`, then left on the issue page the post already links. A GitHub release download that answers
429, 500, 502, 503 or 504 is retried with backoff (run 42474108181 returned 502 on the public URL). When
`GH_TOKEN` is set the bytes come from the GitHub API first, same reason the site build does.

A real run first checks that `https://nordiccrypto.no/newsletter/<id>/` and every story page answer 200, so nothing
goes out before they are live. A story with no page found fails the run.

## State
`data/x_posted.json` records the post id per issue. Any row with `complete`, `tweet_ids` or `url` is skipped, so a
partial record is not posted again. #006 is not in the file (the 8 Nov 2026 run failed before a post).

## Run
```sh
python3 tools/x_newsletter.py --dry-run              # newest issue, print only
python3 tools/x_newsletter.py --issue 002 --dry-run
python3 tools/x_newsletter.py --issue 002            # post (needs the secrets below)
python3 -m unittest tests.test_x_newsletter
```

## Secrets
`X_API_KEY`, `X_API_SECRET` (app consumer keys) and `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` (user tokens for
@nordiccryptobot). The X app must have **Read and Write** permission, and the access token must be generated *after*
setting that. If any is missing, the script logs `skipping: missing …` and exits 0.

## CI
`.github/workflows/x-newsletter.yml` runs after every successful "Deploy site" run, on Monday mornings after the
~08:23 Oslo publish, and on manual dispatch (`issue`, `dry_run`). It commits `data/x_posted.json` back to `main`.
The image step uses the same Cloudflare secrets and variables as "Story illustrations", and `GH_TOKEN` for the
release download. Secrets are not printed.

## Rerun #6 after this is on main

```sh
gh workflow run "X newsletter post" --ref main -f issue=006 -f dry_run=false
```

Or: Actions → X newsletter post → Run workflow, branch `main`, issue `006`, dry run off.
A row for `006` in `data/x_posted.json` means it already went out; the script will not post it again.

## Events and news digests (Telegram mirror)
`tools/x_feed.py` (`.github/workflows/x-feed.yml`) mirrors the Telegram bot on X:

- **News:** one English digest of new stories (`📰 New stories on Nordic Crypto – D.M.YYYY`), each with flag,
  English headline, `Source: <name>`, and `https://nordiccrypto.no/stories/<id>/`.
- **Events:** one post per new upcoming event (title, date/time, venue/address, organiser, Nordic Crypto calendar page).

Same selection rules and Actions-cache ledgers as `telegram-events.yml` (a missing ledger re-seeds and posts nothing).
Triggers after every successful "Deploy site" and on a half-hourly schedule. Manual dispatch supports `news_ids` /
`event_ids` backfill and `dry_run`. Same X secrets as above. Operator name in copy is always "Nordic Crypto" (never
a company suffix); no phone numbers.

```sh
python3 tools/x_feed.py --kind news --ledger /tmp/n.json --dry-run
python3 tools/x_feed.py --kind events --ledger /tmp/e.json --dry-run
python3 -m unittest tests.test_x_feed
```

This supersedes the unmerged digest-only approach in PR #206 (that branch never shipped; this also covers events).

