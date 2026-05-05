# SFO Rust Rewrite

The Rust rewrite lives beside the current Python app while feature parity is built incrementally.

## Current Slices

- `crates/sfo-core`: shared domain types.
- `crates/sfo-db`: SQLite connection and migrations.
- `crates/sfo-server`: Axum server shell.
- `crates/sfo-services`: use-case rules for projects, tasks, and inbox quick capture.

## Current API

- `GET /healthz`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `PATCH /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `PATCH /api/v1/tasks/{task_id}`
- `DELETE /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/complete`
- `POST /api/v1/tasks/{task_id}/reopen`
- `POST /api/v1/tasks/{task_id}/archive`
- `POST /api/v1/tasks/{task_id}/restore`
- `POST /api/v1/inbox/quick-capture`
- `POST /api/v1/import/python-sqlite/dry-run`
- `POST /api/v1/export/backup`

## Import And Backup

The Rust importer currently supports dry-run inspection only. It opens a copied Python SFO SQLite database read-only, computes its SHA-256 checksum, reports table row counts, and warns about tables that are not imported in the current slice.

The backup endpoint currently returns a JSON manifest over the Rust database with schema metadata and table counts. Full SQLite snapshot export will be added after the import path can safely map real rows into the Rust schema.

## Local Verification

Run the existing Python suite:

```bash
.venv/bin/python -m pytest
```

Run the new Rust workspace:

```bash
cargo test --workspace
```

Run the Rust server locally:

```bash
SFO_RUST_DATABASE_URL=sqlite://sfo-rust.db cargo run -p sfo-server
curl http://127.0.0.1:8088/healthz
```

## Notes

The current `src-tauri` shell is still the existing Python-backed desktop wrapper. The Rust rewrite will replace that shell in a later milestone after the server and client API stabilize.
