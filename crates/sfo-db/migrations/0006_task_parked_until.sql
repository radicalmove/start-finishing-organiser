ALTER TABLE tasks
ADD COLUMN parked_until TEXT;

CREATE INDEX IF NOT EXISTS idx_tasks_parked_until
ON tasks (parked_until);
