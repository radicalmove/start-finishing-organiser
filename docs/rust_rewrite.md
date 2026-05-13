# SFO Rust Rewrite

The Rust rewrite lives beside the current Python app while feature parity is built incrementally.

## Current Slices

- `crates/sfo-core`: shared domain types.
- `crates/sfo-db`: SQLite connection and migrations.
- `crates/sfo-server`: Axum server shell.
- `crates/sfo-services`: use-case rules for projects, tasks, blocks, inbox processing, guided capture, and Waiting On.
- `src-tauri/launcher`: first static Rust client shell for server connection, auth, Home/Today summary, quick capture, inbox processing, and inline guided inbox conversion.

## Current API

- `GET /healthz`
- `GET /api/v1/auth/status`
- `GET /api/v1/bootstrap`
- `PUT /api/v1/daily-focus`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}/card`
- `PUT /api/v1/projects/{project_id}/card`
- `POST /api/v1/projects/{project_id}/chunks`
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
- Python project `start_date`, `target_date`, `level_of_success`, `why_link_text`, and `drag_points_notes` are preserved where present.
- Python `success_packs` rows are imported and linked through project `legacy_id` values.
- Python `tasks.id` is preserved as Rust `tasks.legacy_id`.
- Python `blocks.id` is preserved as Rust `blocks.legacy_id`.
- Python `waiting_on.id` is preserved as Rust `waiting_on.legacy_id`.
- Task `project_id` values are mapped through imported project `legacy_id` values.
- Block `project_id` and `task_id` values are mapped through imported project/task `legacy_id` values.
- Waiting On `project_id` values are mapped through imported project `legacy_id` values.
- Legacy SQLite timestamps like `2026-01-02 03:04:05` are normalized to RFC 3339 UTC text.
- Re-running the same import is idempotent for imported projects, success packs, tasks, blocks, and waiting items because upserts key off `legacy_id` or project identity.

Unsupported Python tables, including Python `ritual_entries`, are still reported as warnings and are not imported in this slice. The backup endpoint returns a JSON manifest over the Rust database with schema metadata and table counts, including Rust `success_packs` and `ritual_entries`.

## Project Cards

Project cards are the first Start Finishing shaping surface in the Rust app. Review is the main home for the card, while Process can create a lightweight shaped project with success level, why, and an optional first chunk.

The card stores the finish line, optional start date, required target date, success level, why, GATES notes, drag-point notes, budget/space notes, Success Pack fields, and roadmap chunks. Roadmap chunks are normal project-linked tasks so planning stays connected to execution.

## Bootstrap Summary

`GET /api/v1/bootstrap` returns the first daily dashboard contract for future Mac and iPhone clients:

- Active weekly projects.
- Inbox/container counts.
- Today tasks.
- Today blocks.
- Current and next block for the requested time.
- Daily focus from the latest morning ritual entry (`one_thing` and `frog`).
- Ritual completion state for morning/midday/evening and the next expected ritual.
- Waiting On total, due, and overdue counts.
- Compact system state with database status, schema, backup table counts, and supported import tables.

The endpoint defaults to server date/time and accepts optional `date=YYYY-MM-DD` and `time=HH:MM:SS` query parameters for deterministic clients and tests.

`PUT /api/v1/daily-focus` stores the current day's One Thing/Frog by updating or creating the latest morning ritual entry. It accepts:

```json
{
  "date": "2026-05-06",
  "one_thing": "Ship the Rust client shell",
  "frog": "Make the first uncomfortable call"
}
```

## Auth And Server Config

Rust server configuration is environment-first:

- `SFO_RUST_BIND`: bind address, default `127.0.0.1:8088`.
- `SFO_RUST_DATABASE_URL`: SQLite URL, default `sqlite://sfo-rust.db`.
- `SFO_RUST_API_TOKEN`: optional API token. When set, every `/api/v1/*` route except `/api/v1/auth/status` requires `Authorization: Bearer <token>` or `x-sfo-api-token: <token>`.

`GET /healthz` is always unauthenticated so launch agents and local monitors can check process health. `GET /api/v1/auth/status` is also public and returns whether API auth is required; it does not reveal the token.

## Native Client Shell

The first Rust client shell lives in `src-tauri/launcher` and is intentionally static: there is no Node build step and no frontend framework yet. It connects to a configured Rust server URL, stores the server URL and API token in browser local storage, checks `/healthz` and `/api/v1/auth/status`, then renders `GET /api/v1/bootstrap`.

Current shell behavior:

- Server URL and API token form.
- Public health/auth status checks before loading data.
- Home/Today summary from `/api/v1/bootstrap`, with server times displayed as `HH:MM`.
- Compact connected-state chrome so Home/Today starts closer to the first viewport after a successful connection.
- One Thing/Frog editing through `PUT /api/v1/daily-focus`.
- Waiting On and ritual status summaries.
- Quick capture to `POST /api/v1/inbox/quick-capture`.
- Inbox processing list from `GET /api/v1/inbox/containers` with Learning, Enjoy, Park, Recycle, and an undo/restore feedback banner for reversible actions.
- Inline guided conversion from inbox item to task, project, or OPP/Waiting On item through `POST /api/v1/capture/guided`, with decision-card copy and success feedback after conversion.
- New-project conversion defaults the target date from the server's Today value so native date inputs submit a real value.
- New-project conversion infers Personal for obvious personal captures such as appointments, family, home, and health items.
- No automatic Python backend spawn unless `SFO_SPAWN_BACKEND=1` is explicitly set.
- Server CORS preflight support for Tauri production origins.

Token storage is a temporary client-shell compromise. Before using this as a polished production Mac/iPhone client, move token storage to Keychain or platform-secure storage.

For iPhone, note that some production webview origins are HTTPS. If the webview blocks plain HTTP as mixed content, the Mac mini server will need HTTPS through a local certificate, Caddy/nginx, VPN hostname, or a Tauri-native HTTP path.

The first iPhone client should be a fast capture and daily-review client, not a compressed Mac dashboard. See `docs/rust_iphone_workflow.md` for the phone workflow shape and first build sequence.

## Inbox Containers

The first Rust inbox-processing slice keeps the approved Python semantics for reversible low-friction routing:

- `POST /api/v1/inbox/{task_id}/route` moves an active inbox item into `learn_explore`, `enjoy_recover`, or `park_let_go`.
- Routing clears scheduling/project metadata that should not leak into non-work containers, marks the item processed, and keeps the item pending for later review.
- `POST /api/v1/inbox/{task_id}/undo` returns a quick-routed item to the unprocessed inbox.
- `POST /api/v1/inbox/{task_id}/recycle` moves an active inbox item to the inbox recycle bin.
- `POST /api/v1/inbox/{task_id}/restore` returns a recycled or quick-routed item to the unprocessed inbox.
- `GET /api/v1/inbox/containers` returns container counts plus Unprocessed, Learning, Enjoy, Parked, and Recycle bin item lists.

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

The current shell exposes this as an inline clarification form under each unprocessed inbox row.
Task and OPP conversions require an existing project selection because the backend protects against turning inbox material into free-floating work.

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

Run the launcher utility tests:

```bash
node --test src-tauri/launcher/client.test.mjs
```

Check the Tauri shell:

```bash
cargo check --manifest-path src-tauri/Cargo.toml
```

Run the hands-on development shell:

```bash
scripts/run_tauri_dev_shell.sh
```

This builds and opens a debug app bundle named `Start Finishing Organiser Dev.app` with the development-only `com.rcd58.sfo.dev` bundle identifier. Keep production builds on `com.rcd58.sfo`; the dev identity exists only to avoid macOS LaunchServices collisions with an installed/release app while reviewing worktree changes.

See `docs/rust_mac_mini_deployment.md` for the private Mac mini runbook.
See `docs/rust_iphone_workflow.md` for the first iPhone client workflow shape.

## Notes

The current `src-tauri` shell is now a first Rust-server client shell, not the old Python redirect launcher. It is deliberately thin so the next UX review can expose missing Home/Today API support before a larger native client build.

See `docs/rust_rewrite_parity_review.md` for the current product parity and UX sequencing review.
