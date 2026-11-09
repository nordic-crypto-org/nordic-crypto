# News and event sources in D1

Outlets and event sources are rows in the existing D1 database `nordic-crypto-content` (`sources` in `workers/content/migrations/0001_content.sql`). Add one there. Do not add it by editing `sources.json` in git.

`kind` is `news` (the `sources` list `fetch.py` reads) or `event` (the `event_sources` list `events.py` reads). `payload` is the same JSON object that list used to hold: `id`, `name`, `country`, `url`, `type`, and whatever that type needs (`feed`, `ics`, `link_pattern`, and so on). `enabled` is whether a run may request it. `note` is an editor note on the row. The note is not copied into the payload and is not written into `sources.json`.

A source with `"type": "manual"` and `"enabled": false` is for the researcher only. The nightly fetch does not request it. `undoqo-plebs` is one of these rows, already in D1. Passing no `enabled` on a manual source stores it off.

## Add or change a source

From the repo root, with the Cloudflare token and the database id exported (the same ones as `tools/d1_import.py`). Nothing is committed.

```bash
python3 tools/d1_review.py add-source --kind event --json source.json --enabled false --note "Checked by hand."
python3 tools/d1_review.py add-source --kind news --json outlet.json
```

`source.json` is one object, not the whole catalogue. The same id again updates that row. `--kind` picks the list. `--enabled false` keeps the fetch away from it. `--sqlite FILE` writes a local file instead of D1, for a dry run.

The Worker does the same upsert. `Authorization: Bearer` is the `EDITOR_TOKEN` secret.

```json
POST /api/review
{"kind":"source","source_kind":"event","enabled":false,"note":"Checked by hand.","by":"Nordic Crypto redaktør","payload":{"id":"undoqo-plebs","name":"Undoqo Plebs","url":"https://example.org/undoqo-plebs","type":"manual","enabled":false}}
```

Rows are not deleted. `python3 tools/d1_import.py` only inserts ids D1 does not have. A source an editor changed in D1 is not replaced by the copy in git.

## What the fetch and the build read

`fetch.py` and `events.py` still read `sources.json`. They do not open D1 themselves.

When `NC_DATA_SOURCE=d1`, `python3 tools/d1_sync.py restore` runs before the nightly fetch and writes `sources.json` from the `sources` table: news payloads into `sources`, event payloads into `event_sources`. A D1 row replaces the checkout's copy of that id. An id only in D1 is appended. `user_agent`, `min_delay_seconds` and `fetch_workers` stay. The build does the same inside `materialize()` before it reads the file.

The committed `sources.json` stays the offline snapshot. If D1 cannot be read and `NC_D1_FALLBACK=json` is set, restore leaves that snapshot in place and the build uses it too. Without that variable a failed read stops the run, so CI does not quietly fetch an old catalogue.

`GET /api/v1/sources.json` still returns approved rows only (id, name, country, url, and the other public fields). A researcher-only source can be approved and still have `enabled` false.
