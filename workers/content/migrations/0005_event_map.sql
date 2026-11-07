-- Optional verified map link. The payload column already stores every JSON field.
-- map_url is a query column for the same value. Null when the venue address
-- was not checked against the venue's own site. Rows are still not deleted.

ALTER TABLE events ADD COLUMN map_url TEXT;

INSERT INTO schema_meta (key, value) VALUES ('version', '5')
  ON CONFLICT(key) DO UPDATE SET value = excluded.value;
