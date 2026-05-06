ALTER TABLE tasks
ADD COLUMN owner_type TEXT NOT NULL DEFAULT 'mine';

CREATE TABLE IF NOT EXISTS waiting_on (
  id TEXT PRIMARY KEY NOT NULL,
  legacy_id INTEGER UNIQUE,
  project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
  description TEXT NOT NULL,
  person TEXT,
  last_followup TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_waiting_on_project_id
ON waiting_on (project_id);

CREATE INDEX IF NOT EXISTS idx_waiting_on_last_followup
ON waiting_on (last_followup);
