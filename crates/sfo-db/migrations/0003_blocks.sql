CREATE TABLE IF NOT EXISTS blocks (
  id TEXT PRIMARY KEY NOT NULL,
  legacy_id INTEGER UNIQUE,
  title TEXT,
  date TEXT NOT NULL,
  start_time TEXT,
  end_time TEXT,
  block_type TEXT NOT NULL,
  project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
  task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_blocks_date_start
ON blocks (date, start_time);

CREATE INDEX IF NOT EXISTS idx_blocks_project_id
ON blocks (project_id);

CREATE INDEX IF NOT EXISTS idx_blocks_task_id
ON blocks (task_id);
