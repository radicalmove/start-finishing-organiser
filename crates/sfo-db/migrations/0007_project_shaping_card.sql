ALTER TABLE projects
ADD COLUMN start_date TEXT;

ALTER TABLE projects
ADD COLUMN drag_points_notes TEXT;

ALTER TABLE projects
ADD COLUMN gates_notes TEXT;

ALTER TABLE projects
ADD COLUMN budget_notes TEXT;

CREATE TABLE IF NOT EXISTS success_packs (
  project_id TEXT PRIMARY KEY NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  guides TEXT,
  peers TEXT,
  supporters TEXT,
  beneficiaries TEXT,
  updated_at TEXT
);
