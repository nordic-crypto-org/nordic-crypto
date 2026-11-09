-- Academia catalogue (courses, student groups, publications, research groups).
-- payload is the full JSON object from schema/academia.schema.json, so an import drops no field.
-- status is the editorial status. The public page and GET /api/v1/academia*.json
-- show only status = 'approved'. pending, unverified and out stay in the table.
-- dedupe_key is unique per section (course code, group or research name, DOI or URL)
-- so a later batch cannot insert a second copy of an existing row.
-- Rows are not deleted. Taking a row off the public page sets status to 'out'.
-- academia_meta holds the catalogue header (updated, source list, rules). It is not a row.

CREATE TABLE IF NOT EXISTS academia (
  id TEXT PRIMARY KEY,
  section TEXT NOT NULL CHECK (section IN ('courses', 'groups', 'publications', 'research')),
  country TEXT,
  name TEXT,
  code TEXT,
  institution TEXT,
  url TEXT,
  doi TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'out', 'unverified')),
  active INTEGER,
  year INTEGER,
  pub_type TEXT,
  dedupe_key TEXT NOT NULL,
  payload TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS academia_dedupe ON academia (section, dedupe_key);
CREATE INDEX IF NOT EXISTS academia_public ON academia (status, section, country);
CREATE INDEX IF NOT EXISTS academia_code ON academia (section, code);

CREATE TABLE IF NOT EXISTS academia_meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  updated TEXT,
  source_list TEXT,
  works_catalogue TEXT,
  rules TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS academia_no_delete
BEFORE DELETE ON academia
BEGIN
  SELECT RAISE(ABORT, 'academia rows are not deleted');
END;

INSERT INTO schema_meta (key, value) VALUES ('version', '4')
  ON CONFLICT(key) DO UPDATE SET value = excluded.value;
