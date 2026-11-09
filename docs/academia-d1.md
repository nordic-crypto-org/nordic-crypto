# Academia in D1

Schema: `workers/content/migrations/0004_academia.sql`, on the existing database `nordic-crypto-content` (`workers/content/wrangler.toml`). This does not create a database.

- `academia`: one row per course, student group, publication or research group. `section` is `courses`, `groups`, `publications` or `research`. `payload` is the full JSON object from `schema/academia.schema.json`. `status` is `pending`, `approved`, `out` or `unverified`. `dedupe_key` is unique per section (course code, group or research name, DOI, or URL).
- `academia_meta`: the catalogue header (`updated`, source list, works catalogue, rules). Not a public row.
- Rows are not deleted. A row leaves the public page when `status` is no longer `approved`.

The public page and `GET /api/v1/academia.json` show only `status = approved`. Pending groups stay in the table and off the page.

Data flow:

- `data/academia.json` stays in git. It is the offline snapshot. This change does not delete it.
- `python3 tools/d1_import.py --apply-schema` applies the migrations and inserts rows the table does not already have: the snapshot, then `data/academia_batches/*.json`. A second run does not overwrite a row an editor has changed. Deploy and `d1-publish` run that command when `NC_DATA_SOURCE` is `d1`.
- When `NC_DATA_SOURCE=d1`, `build.py` reads the catalogue from D1 before the archive and the academia page. If the table is missing, empty, or the read fails, the build uses `data/academia.json`. The public page still renders.
- `tools/import_academia.py` and `tools/seed_academia.py` upsert D1 when `NC_DATA_SOURCE=d1`. They do not rewrite `data/academia.json` on that path. Without D1, `import_academia.py` still writes the JSON file. `seed_academia.py` refuses to overwrite it unless `--write-json` is passed.

Adding the next city (no code change):

```bash
python3 tools/d1_review.py add-academia --json helsinki-next.json --api
```

The file is a JSON object with `courses`, `groups`, `publications` and/or `research`. Each row carries its own `status`. The same command updates a row that is already stored. `--keep` leaves an existing row as it is. The Worker accepts the same body: `POST /api/review` with `{"kind":"academia", ...}` and `Authorization: Bearer EDITOR_TOKEN`. `"update": true` refreshes a stored row; without it, a stored row is left as it is.

Do not add another batch by editing `build.py`. The files in `data/academia_batches/` are the Copenhagen and Helsinki seed the first deploy inserts. Further cities use the command or the endpoint.

Names already in the table are not inserted again. That covers CBS Bitcoin, Blockchain Student Group @ ITU, COBRA Aarhus, Aalto Bitcoin, and the course codes CS-AJ0100, COMM.NET.500 and LT00DF90.
