CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY NOT NULL,
  legacy_id INTEGER UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL DEFAULT 'work',
  status TEXT NOT NULL DEFAULT 'active',
  size TEXT,
  time_horizon TEXT,
  target_date TEXT,
  level_of_success TEXT,
  why_link_text TEXT,
  active_this_week INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_projects_category_active
ON projects (category, active_this_week);

CREATE INDEX IF NOT EXISTS idx_projects_created_at
ON projects (created_at);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY NOT NULL,
  legacy_id INTEGER UNIQUE,
  project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
  verb_noun TEXT NOT NULL,
  description TEXT,
  in_inbox INTEGER NOT NULL DEFAULT 0,
  archived_from_inbox INTEGER NOT NULL DEFAULT 0,
  intake_intent TEXT NOT NULL DEFAULT 'unprocessed',
  intake_container TEXT NOT NULL DEFAULT 'unprocessed',
  intake_processed_at TEXT,
  when_bucket TEXT NOT NULL DEFAULT 'later',
  block_type TEXT,
  duration_minutes INTEGER,
  priority INTEGER,
  frog INTEGER NOT NULL DEFAULT 0,
  alignment TEXT,
  first_action TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  scheduled_for TEXT,
  resurface_on TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id
ON tasks (project_id);

CREATE INDEX IF NOT EXISTS idx_tasks_bucket_status_created
ON tasks (when_bucket, status, created_at);

CREATE INDEX IF NOT EXISTS idx_tasks_inbox_status_created
ON tasks (in_inbox, status, created_at);
