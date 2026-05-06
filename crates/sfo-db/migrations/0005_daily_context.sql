CREATE TABLE IF NOT EXISTS ritual_entries (
  id TEXT PRIMARY KEY NOT NULL,
  legacy_id INTEGER UNIQUE,
  ritual_type TEXT NOT NULL,
  entry_date TEXT NOT NULL,
  one_thing TEXT,
  frog TEXT,
  midday_one_thing TEXT,
  midday_frog TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ritual_entries_type_date
ON ritual_entries (ritual_type, entry_date);
