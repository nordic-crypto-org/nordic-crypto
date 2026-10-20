-- Remote app switches, set by a signed-in admin on /admin/ and read by the apps at GET /api/flags (src/flags.js).
CREATE TABLE IF NOT EXISTS app_flags (
  key TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL DEFAULT ''
);
