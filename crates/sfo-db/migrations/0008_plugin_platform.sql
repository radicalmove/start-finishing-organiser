CREATE TABLE plugins (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NULL,
  version TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 0,
  trust_level TEXT NOT NULL,
  status TEXT NOT NULL,
  status_detail TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE plugin_capabilities (
  id TEXT PRIMARY KEY,
  plugin_id TEXT NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
  capability TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE(plugin_id, capability)
);

CREATE TABLE plugin_suggestions (
  id TEXT PRIMARY KEY,
  plugin_id TEXT NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NULL,
  detail TEXT NULL,
  payload_json TEXT NOT NULL,
  source_label TEXT NULL,
  source_uri TEXT NULL,
  confidence REAL NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  created_core_kind TEXT NULL,
  created_core_id TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  resolved_at TEXT NULL
);

CREATE INDEX idx_plugin_capabilities_plugin_id ON plugin_capabilities(plugin_id);
CREATE INDEX idx_plugin_suggestions_status_created ON plugin_suggestions(status, created_at);
CREATE INDEX idx_plugin_suggestions_plugin_status ON plugin_suggestions(plugin_id, status);
