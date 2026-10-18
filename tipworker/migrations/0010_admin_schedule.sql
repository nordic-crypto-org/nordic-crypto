-- Campaigns and scheduled posts for /admin/ (src/admin.js). Rows are written with ADMIN_DELIVERY_TOKEN by
-- tools/admin_schedule.py and read only by a signed-in admin (GET /api/admin/schedule). Never in the repo or on the site.
CREATE TABLE IF NOT EXISTS admin_campaigns (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  channels TEXT NOT NULL DEFAULT '',         -- comma-separated
  what TEXT NOT NULL DEFAULT '',
  starts_at TEXT,                            -- Oslo time, ISO
  ends_at TEXT,
  status TEXT NOT NULL,                      -- active | paused | awaiting_approval | done
  updated_at TEXT NOT NULL                   -- UTC ISO
);
CREATE TABLE IF NOT EXISTS admin_schedule (
  id TEXT PRIMARY KEY,
  channel TEXT NOT NULL,
  what TEXT NOT NULL,
  cron TEXT,                                 -- 5-field cron in tz (recurring), or NULL
  tz TEXT NOT NULL DEFAULT 'Europe/Oslo',    -- 'UTC' for GitHub Actions crons
  at TEXT,                                   -- one-off Oslo time, ISO; used when cron is NULL
  status TEXT NOT NULL,                      -- active | paused | awaiting_approval | done
  source TEXT NOT NULL DEFAULT '',           -- e.g. workflow:x-newsletter.yml, routine, campaign
  campaign_id TEXT,                          -- admin_campaigns.id
  updated_at TEXT NOT NULL
);
