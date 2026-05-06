# SFO Rust Rewrite

The Rust rewrite lives beside the current Python app while feature parity is built incrementally.

## Current Slices

- `crates/sfo-core`: shared domain types.
- `crates/sfo-db`: SQLite connection and migrations.
- `crates/sfo-server`: Axum server shell.
- `crates/sfo-services`: use-case rules for projects, tasks, blocks, inbox processing, guided capture, and Waiting On.

## Current API

- `GET /healthz`
- `GET /api/v1/auth/status`
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
- `POST /api/v1/capture/guided`
- `GET /api/v1/waiting`
- `POST /api/v1/waiting`
- `PATCH /api/v1/waiting/{waiting_id}`
- `POST /api/v1/waiting/{waiting_id}/resolve`
- `POST /api/v1/import/python-sqlite/dry-run`
- `POST /api/v1/import/python-sqlite`
- `POST /api/v1/export/backup`

## Import And Backup

The Rust importer supports dry-run inspection and real import for the current project/task/block/waiting slice. Dry-run opens a copied Python SFO SQLite database read-only, computes its SHA-256 checksum, reports table row counts, and warns about tables that are not imported in the current slice.

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
- Python `waiting_on.id` is preserved as Rust `waiting_on.legacy_id`.
- Task `project_id` values are mapped through imported project `legacy_id` values.
- Block `project_id` and `task_id` values are mapped through imported project/task `legacy_id` values.
- Waiting On `project_id` values are mapped through imported project `legacy_id` values.
- Legacy SQLite timestamps like `2026-01-02 03:04:05` are normalized to RFC 3339 UTC text.
- Re-running the same import is idempotent for imported projects, tasks, blocks, and waiting items because upserts key off `legacy_id`.

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

## Auth And Server Config

Rust server configuration is environment-first:

- `SFO_RUST_BIND`: bind address, default `127.0.0.1:8088`.
- `SFO_RUST_DATABASE_URL`: SQLite URL, default `sqlite://sfo-rust.db`.
- `SFO_RUST_API_TOKEN`: optional API token. When set, every `/api/v1/*` route except `/api/v1/auth/status` requires `Authorization: Bearer <token>` or `x-sfo-api-token: <token>`.

`GET /healthz` is always unauthenticated so launch agents and local monitors can check process health. `GET /api/v1/auth/status` is also public and returns whether API auth is required; it does not reveal the token.

## Inbox Containers

The first Rust inbox-processing slice keeps the approved Python semantics for reversible low-friction routing:

- `POST /api/v1/inbox/{task_id}/route` moves an active inbox item into `learn_explore`, `enjoy_recover`, or `park_let_go`.
- Routing clears scheduling/project metadata that should not leak into non-work containers, marks the item processed, and keeps the item pending for later review.
- `POST /api/v1/inbox/{task_id}/undo` returns a quick-routed item to the unprocessed inbox.
- `POST /api/v1/inbox/{task_id}/recycle` moves an active inbox item to the inbox recycle bin.
- `POST /api/v1/inbox/{task_id}/restore` returns a recycled or quick-routed item to the unprocessed inbox.
- `GET /api/v1/inbox/containers` returns container counts plus Learning, Enjoy, Parked, and Recycle bin item lists.

## Guided Capture

`POST /api/v1/capture/guided` is the first Rust API for the primary `Process` path:

- Create a clarified task from guided capture input.
- Create a clarified project with target-date and action-title checks.
- Preserve `year` as a project horizon while mapping `year` task captures to the `later` task bucket.
- Process an inbox source item by requiring an explicit `inbox_intent`.
- Route source inbox items to Learning, Enjoy, or Parked without creating duplicate task backlog.
- Convert a source inbox item into an actionable support-project task only when an existing `project_id` is supplied.
- Mark a source inbox item as processed/archived when it becomes a new project.
- Create a Waiting On item when `owner_type` is `opp`, using `waiting_person` when supplied.

## Waiting On / OPP

The Rust rewrite now has a first-class Waiting On backend:

- `GET /api/v1/waiting` returns paginated waiting items.
- `POST /api/v1/waiting` creates an item with description, optional person, optional project, and optional follow-up date.
- `PATCH /api/v1/waiting/{waiting_id}` updates fields and supports `null` to clear optional values.
- `POST /api/v1/waiting/{waiting_id}/resolve` deletes/resolves the waiting item.
- Tasks now store `owner_type` as `mine`, `shared`, or `opp`.

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

See `docs/rust_mac_mini_deployment.md` for the private Mac mini runbook.

## Notes

The current `src-tauri` shell is still the existing Python-backed desktop wrapper. The Rust rewrite will replace that shell in a later milestone after the server and client API stabilize.

See `docs/rust_rewrite_parity_review.md` for the current product parity and UX sequencing review.
