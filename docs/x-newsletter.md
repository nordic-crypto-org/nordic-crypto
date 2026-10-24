# Newsletter → X long post (@nordiccryptobot)

`tools/x_newsletter.py` posts each new weekly Nordic Crypto issue to X once, as **one long post** (X Premium) with the
newsreel video attached (X API v2 chunked upload `/2/media/upload`). Never a thread: if X rejects the post, the run
fails and nothing is posted.

```
Nordic Crypto #N: <headline>
https://nordiccrypto.no/newsletter/<id>/

<story headline>
https://nordiccrypto.no/stories/<story id>/
…
```

Every story links to its page on nordiccrypto.no, never the original source. Story ids come from `data/news.json`
and `archive/articles.json`, matched on the source URL in `issue.html`. X refuses posts with too many links (issue #3
with 64 failed, #1 with 20 went through), so the post carries at most 20 (`MAX_URLS`); later stories are listed under
"More in the issue:" without a link.

Data comes from `newsletter/published/issues.json` and `newsletter/published/<id>/issue.html`. The video is the local
`video.mp4` or `video.url` (sha256-checked). A real run first checks that `https://nordiccrypto.no/newsletter/<id>/`
and every story page answer 200, so nothing goes out before they are live. A story with no page found fails the run.

## State
`data/x_posted.json` records the post id per issue. A completed issue is never posted again.

## Run
```sh
python3 tools/x_newsletter.py --dry-run              # newest issue, print only
python3 tools/x_newsletter.py --issue 002 --dry-run
python3 tools/x_newsletter.py --issue 002            # post (needs the secrets below)
python3 -m pytest tests/test_x_newsletter.py
```

## Secrets
`X_API_KEY`, `X_API_SECRET` (app consumer keys) and `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` (user tokens for
@nordiccryptobot). The X app must have **Read and Write** permission, and the access token must be generated *after*
setting that. If any is missing, the script logs `skipping: missing …` and exits 0.

## CI
`.github/workflows/x-newsletter.yml` runs after every successful "Deploy site" run, on Monday mornings after the
~08:23 Oslo publish, and on manual dispatch (`issue`, `dry_run`). It commits `data/x_posted.json` back to `main`.

## Daily news digest
`tools/x_daily.py` (`.github/workflows/x-daily.yml`, after every successful "Deploy site" and hourly at :37) posts one
English digest per Oslo day of the stories not yet in a digest: `📰 New on Nordic Crypto – 18 Oct 2026`, then per story
the flag, English headline (`title_en`, else `title_i18n.en`) and `https://nordiccrypto.no/stories/<id>/`. Past 280
characters it becomes a thread. It waits until every new story has its headline and summary in all site languages (as
`tools/story_translate.py` plans them) and its page answers 200; from 18:00 Oslo it posts the ready ones and the rest go
in a later digest. Stories after the day's digest go in the next day's. `data/x_daily_posted.json` records each day.
Same secrets as above. `python3 tools/x_daily.py --dry-run`; tests: `python3 -m unittest tests.test_x_daily`.
