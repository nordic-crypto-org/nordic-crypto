#!/usr/bin/env python3
"""Academia rows in the existing nordic-crypto-content D1 database.

The public page and the public API show only status=approved. The git file
data/academia.json stays the offline snapshot. A new city batch is a JSON
document passed to tools/d1_review.py add-academia (or POST /api/review),
not a change to this module.

data/academia_batches/*.json is the cutover seed. The deploy import inserts
rows D1 does not already have and does not overwrite an editor's later edit.
"""
import json
import os
import re
import unicodedata

from tools import d1_store

SECTIONS = ("courses", "groups", "publications", "research")
STATUSES = ("pending", "approved", "out", "unverified")
BATCH_DIR = ("data", "academia_batches")

# A batch must not add a second row for these. The token has to appear in the
# incoming name or course code AND in a row already stored in that section.
GUARDS = (
    ("groups", ("cbs bitcoin",)),
    ("groups", ("blockchain student group",)),
    ("groups", ("aalto bitcoin",)),
    ("research", ("cobra",)),
    ("courses", ("cs-aj0100",)),
    ("courses", ("comm.net.500",)),
    ("courses", ("lt00df90",)),
)


def norm_name(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def course_code(value):
    return re.sub(r"\s+", "", str(value or "")).upper()


def row_blob(row):
    parts = [row.get("name"), row.get("title"), row.get("code")]
    return " ".join(str(part) for part in parts if part).lower()


def dedupe_key(section, row):
    """Stable identity inside one section. Same key means the same listing."""
    if section == "publications":
        doi = str(row.get("doi") or "").strip().lower()
        if doi:
            return "doi:" + doi
        url = d1_store.canon(row.get("url"))
        return "url:" + url if url else ""
    if section == "courses":
        code = course_code(row.get("code"))
        country = str(row.get("country") or "").strip().upper()
        if code:
            return f"code:{country}:{code}"
        url = d1_store.canon(row.get("url"))
        return "url:" + url if url else ""
    name = norm_name(row.get("name") or row.get("title"))
    if name:
        return "name:" + name
    url = d1_store.canon(row.get("url"))
    return "url:" + url if url else ""


def safe_id(value):
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    return text[:120]


def assign_id(section, row, n, used):
    """Same shape as tools/api_feed.py _row_id, stored so the Worker and the static API agree."""
    if section == "publications" and row.get("doi"):
        base = "doi-" + safe_id(str(row["doi"]).replace("/", "_"))
    elif section == "courses" and row.get("code"):
        base = safe_id(f"{row.get('country') or 'xx'}-{row['code']}")
    elif row.get("url"):
        tail = re.sub(r"^https?://", "", str(row["url"])).strip("/")
        base = safe_id(f"{section}-{tail}")
    else:
        base = safe_id(row.get("name") or row.get("title") or f"{section}-{n}")
    base = (base or f"{section}-{n}")[:120]
    cand, i = base, 2
    while cand in used:
        cand = f"{base}-{i}"
        i += 1
    used.add(cand)
    return cand


def _guarded(section, row, blobs):
    blob = row_blob(row)
    if not blob:
        return False
    for sec, tokens in GUARDS:
        if sec != section:
            continue
        if not all(token in blob for token in tokens):
            continue
        for existing_section, existing_blob in blobs:
            if existing_section == section and all(token in existing_blob for token in tokens):
                return True
    return False


def _institution(value):
    if isinstance(value, list):
        return ", ".join(str(part) for part in value if part)
    if isinstance(value, str):
        return value
    return None


def _active(section, row):
    if section != "groups":
        return None
    if row.get("active") is True:
        return 1
    if row.get("active") is False:
        return 0
    return None


def _year(row):
    year = row.get("year")
    return year if isinstance(year, int) else None


def _require_table(store):
    if d1_store.schema_version(store) < 4:
        raise d1_store.D1Error(
            "academia table is missing. Run python3 tools/d1_import.py --apply-schema"
        )


def _blank_section_stats():
    return {"inserted": 0, "updated": 0, "unchanged": 0, "kept": 0, "guarded": 0}


def _totals(stats):
    out = _blank_section_stats()
    for row in stats["sections"].values():
        for key in out:
            out[key] += row[key]
    stats.update(out)
    return stats


def _load_existing(store):
    rows = store.query(
        "SELECT id, section, dedupe_key, name, code, content_hash, payload FROM academia",
        (),
    )
    by_key = {}
    blobs = []
    used = set()
    for row in rows:
        by_key[(row["section"], row["dedupe_key"])] = row
        payload = json.loads(row["payload"])
        blobs.append((row["section"], row_blob(payload)))
        if row.get("id"):
            used.add(row["id"])
        if payload.get("id"):
            used.add(payload["id"])
    return by_key, blobs, used


def _write_meta(store, doc, at):
    rules = doc.get("rules") if isinstance(doc.get("rules"), list) else []
    rules = [rule for rule in rules if isinstance(rule, str)]
    store.execute(
        """
        INSERT INTO academia_meta (id, updated, source_list, works_catalogue, rules, updated_at)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          updated = excluded.updated,
          source_list = excluded.source_list,
          works_catalogue = excluded.works_catalogue,
          rules = excluded.rules,
          updated_at = excluded.updated_at
        """,
        (
            doc.get("updated"),
            doc.get("source_list"),
            doc.get("works_catalogue"),
            json.dumps(rules, ensure_ascii=False),
            at,
        ),
    )


def _row_values(section, row, row_id, key):
    payload = dict(row)
    payload["id"] = row_id
    text = d1_store.dumps(payload)
    return {
        "id": row_id,
        "section": section,
        "country": row.get("country"),
        "name": row.get("name") or row.get("title"),
        "code": row.get("code"),
        "institution": _institution(row.get("institution")),
        "url": row.get("url"),
        "doi": (str(row.get("doi")).strip().lower() if row.get("doi") else None),
        "status": row.get("status"),
        "active": _active(section, row),
        "year": _year(row),
        "pub_type": row.get("type") if section == "publications" else None,
        "dedupe_key": key,
        "payload": text,
        "content_hash": d1_store.digest(text),
    }


def upsert_document(store, doc, at, actor="import", update=False, update_meta=False):
    """Insert rows D1 does not have. update=True also refreshes a matching row.

    A guard match against a different existing row is never inserted or updated.
    That is what keeps CBS Bitcoin, COBRA Aarhus and the named courses singular.
    """
    _require_table(store)
    if not isinstance(doc, dict):
        raise d1_store.D1Error("academia document must be a JSON object")
    stats = {"sections": {section: _blank_section_stats() for section in SECTIONS}, "guarded_names": []}
    by_key, blobs, used = _load_existing(store)
    n = 0
    for section in SECTIONS:
        rows = doc.get(section) or []
        if not isinstance(rows, list):
            raise d1_store.D1Error("academia " + section + " must be a list")
        for row in rows:
            n += 1
            if not isinstance(row, dict):
                raise d1_store.D1Error("an academia row is not an object")
            status = row.get("status")
            if status not in STATUSES:
                raise d1_store.D1Error(
                    "an academia row has a status outside pending, approved, out, unverified"
                )
            key = dedupe_key(section, row)
            if not key or key.endswith(":"):
                raise d1_store.D1Error("an academia row needs a name, course code, DOI or url")
            label = row.get("name") or row.get("title") or row.get("code") or key
            existing = by_key.get((section, key))
            if existing is None and _guarded(section, row, blobs):
                stats["sections"][section]["guarded"] += 1
                stats["guarded_names"].append(label)
                continue
            if existing is None:
                row_id = assign_id(section, row, n, used)
                values = _row_values(section, row, row_id, key)
                store.execute(
                    """
                    INSERT INTO academia (
                      id, section, country, name, code, institution, url, doi, status, active, year,
                      pub_type, dedupe_key, payload, content_hash, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        values["id"], values["section"], values["country"], values["name"], values["code"],
                        values["institution"], values["url"], values["doi"], values["status"], values["active"],
                        values["year"], values["pub_type"], values["dedupe_key"], values["payload"],
                        values["content_hash"], at, at,
                    ),
                )
                d1_store.audit(store, "academia", row_id, "import", actor, at, section)
                stored = dict(values, payload=values["payload"])
                by_key[(section, key)] = stored
                blobs.append((section, row_blob(row)))
                stats["sections"][section]["inserted"] += 1
                continue
            values = _row_values(section, row, existing["id"], key)
            if existing["content_hash"] == values["content_hash"]:
                stats["sections"][section]["unchanged"] += 1
                continue
            if not update:
                stats["sections"][section]["kept"] += 1
                continue
            store.execute(
                """
                UPDATE academia SET
                  country = ?, name = ?, code = ?, institution = ?, url = ?, doi = ?, status = ?,
                  active = ?, year = ?, pub_type = ?, payload = ?, content_hash = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values["country"], values["name"], values["code"], values["institution"], values["url"],
                    values["doi"], values["status"], values["active"], values["year"], values["pub_type"],
                    values["payload"], values["content_hash"], at, existing["id"],
                ),
            )
            d1_store.audit(store, "academia", existing["id"], "import", actor, at, "updated")
            existing["content_hash"] = values["content_hash"]
            existing["payload"] = values["payload"]
            stats["sections"][section]["updated"] += 1
    if update_meta or not d1_store.one(store, "SELECT id FROM academia_meta WHERE id = 1"):
        if any(doc.get(key) is not None for key in ("updated", "rules", "source_list", "works_catalogue")):
            _write_meta(store, doc, at)
    stats = _totals(stats)
    stats["counts"] = counts(store)
    return stats


def document(store):
    """Full catalogue, every status. None when this database has no academia table."""
    if d1_store.schema_version(store) < 4:
        return None
    meta = d1_store.one(store, "SELECT updated, source_list, works_catalogue, rules FROM academia_meta WHERE id = 1")
    rules = []
    if meta and meta.get("rules"):
        try:
            parsed = json.loads(meta["rules"])
            if isinstance(parsed, list):
                rules = [rule for rule in parsed if isinstance(rule, str)]
        except json.JSONDecodeError:
            rules = []
    doc = {
        "updated": (meta or {}).get("updated"),
        "source_list": (meta or {}).get("source_list") or "",
        "works_catalogue": (meta or {}).get("works_catalogue") or "",
        "rules": rules,
        "courses": [],
        "groups": [],
        "publications": [],
        "research": [],
    }
    for row in store.query("SELECT section, payload FROM academia ORDER BY section, country, name, id", ()):
        section = row["section"]
        if section not in doc:
            continue
        doc[section].append(json.loads(row["payload"]))
    return doc


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def backup_document(store):
    """Catalogue for the private backup. Addresses are redacted so the privacy gate can run on it."""
    doc = document(store) or {
        "updated": None, "source_list": "", "works_catalogue": "", "rules": [],
        "courses": [], "groups": [], "publications": [], "research": [],
    }
    redacted = json.loads(_EMAIL.sub("[redacted]", json.dumps(doc, ensure_ascii=False)))
    redacted["counts"] = counts(store)
    return redacted


def public_sections(doc):
    """Rows the public page and the public API may show."""
    doc = doc or {}
    return {
        section: [dict(row) for row in (doc.get(section) or []) if row.get("status") == "approved"]
        for section in SECTIONS
    }


def _bump_updated(store, day, at):
    """Keep the catalogue date moving forward when a batch is newer than the git file."""
    if not day or d1_store.schema_version(store) < 4:
        return
    meta = d1_store.one(store, "SELECT updated FROM academia_meta WHERE id = 1")
    if not meta:
        return
    if str(day) > str(meta.get("updated") or ""):
        store.execute(
            "UPDATE academia_meta SET updated = ?, updated_at = ? WHERE id = 1",
            (day, at),
        )


def counts(store):
    total = d1_store.one(store, "SELECT COUNT(*) AS n FROM academia", ())
    approved = d1_store.one(store, "SELECT COUNT(*) AS n FROM academia WHERE status = 'approved'", ())
    by_section = {}
    for section in SECTIONS:
        row = d1_store.one(
            store,
            "SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved FROM academia WHERE section = ?",
            (section,),
        )
        by_section[section] = {"total": row["n"] or 0, "approved": row["approved"] or 0}
    return {"total": total["n"] if total else 0, "approved": approved["n"] if approved else 0, "sections": by_section}


def _batch_paths(root):
    directory = os.path.join(root, *BATCH_DIR)
    if not os.path.isdir(directory):
        return []
    return [
        os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.endswith(".json")
    ]


def import_checkout(store, root, at, actor="import"):
    """Insert data/academia.json, then the cutover batches. Existing D1 rows stay."""
    stats = {
        "file": _blank_section_stats(),
        "sections": {section: _blank_section_stats() for section in SECTIONS},
        "batches": [],
        "guarded_names": [],
    }
    path = os.path.join(root, "data", "academia.json")
    doc = d1_store.load_json(path, None)
    if isinstance(doc, dict):
        file_stats = upsert_document(store, doc, at, actor, update=False, update_meta=True)
        stats["file"] = {key: file_stats[key] for key in _blank_section_stats()}
        stats["sections"] = file_stats["sections"]
        stats["guarded_names"].extend(file_stats["guarded_names"])
    for batch_path in _batch_paths(root):
        batch = d1_store.load_json(batch_path, None)
        if not isinstance(batch, dict):
            continue
        batch_stats = upsert_document(store, batch, at, actor, update=False, update_meta=False)
        stats["batches"].append({
            "file": os.path.basename(batch_path),
            **{key: batch_stats[key] for key in _blank_section_stats()},
            "guarded_names": batch_stats["guarded_names"],
        })
        stats["guarded_names"].extend(batch_stats["guarded_names"])
        for section in SECTIONS:
            for key in _blank_section_stats():
                stats["sections"][section][key] += batch_stats["sections"][section][key]
        _bump_updated(store, batch.get("updated"), at)
    _totals(stats)
    if d1_store.schema_version(store) >= 4:
        stats["counts"] = counts(store)
    else:
        stats["counts"] = {"total": 0, "approved": 0, "sections": {}}
    return stats


def brief(stats):
    """One line for the import log. No row text."""
    counts_row = stats.get("counts") or {}
    return (
        f"inserted {stats.get('inserted', 0)}, updated {stats.get('updated', 0)}, "
        f"unchanged {stats.get('unchanged', 0)}, kept {stats.get('kept', 0)}, "
        f"guarded {stats.get('guarded', 0)}; "
        f"table {counts_row.get('total', 0)} ({counts_row.get('approved', 0)} approved)"
    )
