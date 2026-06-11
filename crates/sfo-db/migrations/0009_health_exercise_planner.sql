CREATE TABLE health_exercise_sessions (
  id TEXT PRIMARY KEY,
  session_date TEXT NOT NULL,
  session_type TEXT NOT NULL,
  title TEXT NOT NULL,
  target_duration_minutes INTEGER NULL,
  status TEXT NOT NULL,
  notes TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE health_gym_exercises (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES health_exercise_sessions(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  exercise_name TEXT NOT NULL,
  sets INTEGER NULL,
  reps INTEGER NULL,
  weight REAL NULL,
  weight_unit TEXT NULL,
  notes TEXT NULL
);

CREATE TABLE health_cardio_exercises (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES health_exercise_sessions(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  activity_type TEXT NOT NULL,
  duration_minutes INTEGER NULL,
  intensity TEXT NULL,
  notes TEXT NULL
);

CREATE TABLE health_flexibility_exercises (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES health_exercise_sessions(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  movement_name TEXT NOT NULL,
  sets INTEGER NULL,
  hold_seconds INTEGER NULL,
  side TEXT NULL,
  notes TEXT NULL
);

CREATE INDEX idx_health_exercise_sessions_date ON health_exercise_sessions(session_date);
CREATE INDEX idx_health_exercise_sessions_type ON health_exercise_sessions(session_type);
CREATE INDEX idx_health_gym_exercises_session ON health_gym_exercises(session_id);
CREATE INDEX idx_health_cardio_exercises_session ON health_cardio_exercises(session_id);
CREATE INDEX idx_health_flexibility_exercises_session ON health_flexibility_exercises(session_id);
