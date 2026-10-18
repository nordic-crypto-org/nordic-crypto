-- Press release sends for /admin/ (src/admin.js). Recipients are personal data: readable only with an admin session,
-- written only with ADMIN_DELIVERY_TOKEN by tools/press_history.py. The public release list is data/press/history.json.
CREATE TABLE IF NOT EXISTS press_sends (
  id TEXT PRIMARY KEY,                       -- <release id>-<Oslo yyyymmddhhmmss>[-dry], made by tools/press_history.py
  release_id TEXT NOT NULL,
  at TEXT NOT NULL,                          -- Oslo time, ISO with offset
  from_addr TEXT NOT NULL,
  dry_run INTEGER NOT NULL DEFAULT 0,
  sent INTEGER NOT NULL DEFAULT 0,
  failed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS press_sends_release ON press_sends(release_id, at);
CREATE TABLE IF NOT EXISTS press_send_recipients (
  send_id TEXT NOT NULL,                     -- press_sends.id
  email TEXT NOT NULL,
  status TEXT NOT NULL,                      -- sent | failed | dry_run
  error TEXT NOT NULL DEFAULT '',            -- short provider reason, never the address
  PRIMARY KEY (send_id, email)
);
