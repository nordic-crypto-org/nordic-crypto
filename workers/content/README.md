# Story and event review (Cloudflare D1)

The public site stays on GitHub Pages. This Worker is the editor API and an optional live copy of the approved rows.

`NC_DATA_SOURCE` must be `d1` before the site reads D1. Until then, `data/news.json` and `data/events.json` are the source. The full steps, the secret names and the free-tier limits are in the main README under [Stories and events in D1](../../README.md#stories-and-events-in-d1).

`setup.sh` prints the commands. It creates the database only when `CLOUDFLARE_API_TOKEN` is set and you pass `--apply`. Without the token it exits and creates nothing.

## Routes

| Method | Path | Auth | What |
|---|---|---|---|
| GET | `/api/v1/news.json` and `/api/v1/news/:id.json` | no | Approved stories. No teasers, match rules or reject reasons. `image.url` when a story illustration is stored. The prompt is not included. |
| GET | `/story-images/:id.png` | no | That illustration, from the R2 binding `STORY_IMAGES`. 404 when the bucket is not bound or the object is missing. |
| GET | `/api/v1/events.json` and `/api/v1/events/:id.json` | no | Approved events. |
| GET | `/api/v1/sources.json` | no | Approved outlets: id, name, country, url, enabled. |
| GET | `/api/review/pending` | `Authorization: Bearer EDITOR_TOKEN` | Ids and titles waiting on the editor. |
| POST | `/api/review` | the same token | `{kind: story\|event, id, action: approve\|reject, summary, reason, by}`, or `{kind: source, source_kind: news\|event, payload, enabled, note, by}` to upsert a source. |

A story approval requires `summary`. The row stores `reviewed_by` and `reviewed_at`. Rows are not deleted.

If `GITHUB_DISPATCH_TOKEN` is set, an approval asks GitHub to run the `d1-publish` workflow (`repository_dispatch`, event type `d1-approved`). Without that secret the schedule (07:17 and 15:17 UTC) publishes instead. The approval itself still sticks.

## Commands

The token needs Account → D1 → Edit and Account → Workers Scripts → Edit. Do not reuse `CF_ANALYTICS_TOKEN`.

```bash
export CLOUDFLARE_API_TOKEN='…'
export CLOUDFLARE_ACCOUNT_ID='…'
export CF_ACCOUNT_ID="$CLOUDFLARE_ACCOUNT_ID"

npx wrangler d1 create nordic-crypto-content
# replace the zeros in wrangler.toml with the database_id
npx wrangler d1 migrations apply nordic-crypto-content --remote

export CF_D1_DATABASE_ID='…'
python3 ../../tools/d1_import.py

npx wrangler secret put EDITOR_TOKEN
npx wrangler deploy

gh secret set CLOUDFLARE_API_TOKEN
gh variable set CF_ACCOUNT_ID --body "$CF_ACCOUNT_ID"
gh variable set CF_D1_DATABASE_ID --body "$CF_D1_DATABASE_ID"
gh variable set NC_DATA_SOURCE --body d1
```

Story images (the R2 bucket, these migrations, and this deploy) can be done from Actions: **Set up story images** (`.github/workflows/story-images-setup.yml`). It does not set `CF_R2_STORY_BUCKET`.

Review from the repo root, which shells out to `wrangler d1 execute`:

```bash
python3 tools/d1_review.py pending
python3 tools/d1_review.py approve --id STORY_ID --summary "…" --by "Nordic Crypto redaktør"
python3 tools/d1_review.py reject --id STORY_ID --reason "…"
python3 tools/d1_review.py approve-event --id EVENT_ID
python3 tools/d1_review.py reject-event --id EVENT_ID --reason "…"
python3 tools/d1_review.py add-source --kind event --json source.json --enabled false --note "Checked by hand."
```

`add-source` writes the `sources` table. It does not edit `sources.json`. A `type: manual` source with `enabled` false is researcher-only and is never fetched. See [News and event sources in D1](../../docs/sources-d1.md).

Test: `node --test workers/content/test/worker.test.js` from the repo root, and `python3 -m unittest tests.test_d1_store tests.test_d1_sources`.
