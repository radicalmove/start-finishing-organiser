# SFO Rust Rewrite

The Rust rewrite lives beside the current Python app while feature parity is built incrementally.

## Current Slices

- `crates/sfo-core`: shared domain types.
- `crates/sfo-db`: SQLite connection and migrations.
- `crates/sfo-server`: Axum server shell.
- `crates/sfo-services`: use-case rules for projects, tasks, blocks, and inbox processing.

## Current API

- `GET /healthz`
- `GET /api/v1/bootstrap`
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
- `GET /api/v1/blocks`
- `POST /api/v1/blocks`
- `PATCH /api/v1/blocks/{block_id}`
- `DELETE /api/v1/blocks/{block_id}`
- `GET /api/v1/inbox/containers`
- `POST /api/v1/inbox/quick-capture`
- `POST /api/v1/inbox/{task_id}/route`
- `POST /api/v1/inbox/{task_id}/undo`
- `POST /api/v1/inbox/{task_id}/recycle`
- `POST /api/v1/inbox/{task_id}/restore`
- `POST /api/v1/import/python-sqlite/dry-run`
- `POST /api/v1/import/python-sqlite`
- `POST /api/v1/export/backup`

## Import And Backup

The Rust importer supports dry-run inspection and real import for the current project/task/block slice. Dry-run opens a copied Python SFO SQLite database read-only, computes its SHA-256 checksum, reports table row counts, and warns about tables that are not imported in the current slice.

Real import is exposed at `POST /api/v1/import/python-sqlite` with:

```json
{
  "source_path": "/path/to/copied-python-sfo.db",
  "backup_dir": "/path/to/backups"
}
```

`backup_dir` is optional and defaults to `backups`. Before any import writes, the Rust app creates a migrated SQLite backup file of the current Rust database. The importer then upserts supported legacy rows in one transaction:

- Python `projects.id` is preserved as Rust `projects.legacy_id`.
- Python `tasks.id` is preserved as Rust `tasks.legacy_id`.
- Python `blocks.id` is preserved as Rust `blocks.legacy_id`.
- Task `project_id` values are mapped through imported project `legacy_id` values.
- Block `project_id` and `task_id` values are mapped through imported project/task `legacy_id` values.
- Legacy SQLite timestamps like `2026-01-02 03:04:05` are normalized to RFC 3339 UTC text.
- Re-running the same import is idempotent for imported projects, tasks, and blocks because upserts key off `legacy_id`.

Unsupported Python tables are still reported as warnings and are not imported in this slice. The backup endpoint returns a JSON manifest over the Rust database with schema metadata and table counts.

## Bootstrap Summary

`GET /api/v1/bootstrap` returns the first daily dashboard contract for future Mac and iPhone clients:

- Active weekly projects.
- Inbox/container counts.
- Today tasks.
- Today blocks.
- Current and next block for the requested time.
- Compact system state with database status, schema, backup table counts, and supported import tables.

The endpoint defaults to server date/time and accepts optional `date=YYYY-MM-DD` and `time=HH:MM:SS` query parameters for deterministic clients and tests.

## Inbox Containers

The first Rust inbox-processing slice keeps the approved Python semantics for reversible low-friction routing:

- `POST /api/v1/inbox/{task_id}/route` moves an active inbox item into `learn_explore`, `enjoy_recover`, or `park_let_go`.
- Routing clears scheduling/project metadata that should not leak into non-work containers, marks the item processed, and keeps the item pending for later review.
- `POST /api/v1/inbox/{task_id}/undo` returns a quick-routed item to the unprocessed inbox.
- `POST /api/v1/inbox/{task_id}/recycle` moves an active inbox item to the inbox recycle bin.
- `POST /api/v1/inbox/{task_id}/restore` returns a recycled or quick-routed item to the unprocessed inbox.
- `GET /api/v1/inbox/containers` returns container counts plus Learning, Enjoy, Parked, and Recycle bin item lists.

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

See `docs/rust_rewrite_parity_review.md` for the current product parity and UX sequencing review.
