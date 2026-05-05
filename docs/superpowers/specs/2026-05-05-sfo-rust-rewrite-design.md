# SFO Rust Rewrite Design

## Context

SFO is currently a single-user FastAPI/Jinja/SQLite app with a Tauri macOS wrapper that spawns a bundled Python backend. The app has grown into several product areas: projects, tasks, inbox capture and processing, blocks, resurfacing, weekly review, waiting-on, rituals, health tracking, coach guidance, Gmail import, export, authentication, and lightweight schema migrations.

The rewrite direction is to make Rust the product architecture rather than only the desktop shell. The current Python app remains the behavioral reference and migration source until the Rust app reaches feature parity. RADsuite provides the closest local precedent: a Rust workspace, Axum server, SQLx database layer, Tauri client, and Mac mini deployment model. SFO should reuse that shape without copying RADsuite's offline-first sync complexity.

## Goals

- Build a full Rust replacement for SFO in small, verifiable slices.
- Run the canonical database on the user's Mac mini server.
- Support both macOS and iPhone clients against the same server data.
- Keep the app single-user first, but avoid schema and API choices that would block future multi-device or limited sharing.
- Preserve current user data through an explicit import path from the Python SQLite database.
- Make every rewrite step testable before moving to the next product area.

## Non-Goals

- Do not build offline-first sync in the first rewrite. The first iPhone version may require network access to the Mac mini through local network or VPN.
- Do not port every Python route mechanically. The Rust API should model product behavior through services and contracts, not reproduce route-level implementation quirks.
- Do not introduce PostgreSQL until SQLite becomes a demonstrated constraint.
- Do not make Gmail, coach LLM, or complex health analytics part of the first vertical slice.

## Recommended Architecture

The Rust rewrite should be a server-first workspace with a shared domain crate and thin clients:

- `crates/sfo-core`: domain types, enums, IDs, API DTOs, validation errors, and shared time/date helpers.
- `crates/sfo-db`: SQLx migrations, SQLite connection setup, repositories, import helpers, and backup primitives.
- `crates/sfo-server`: Axum HTTP API, auth, routing, service orchestration, health checks, backup/export endpoints, and server configuration.
- `crates/sfo-services`: use-case logic for projects, tasks, inbox, weekly review, waiting-on, health, coach, and integrations.
- `apps/desktop`: Tauri macOS app that talks to the server instead of spawning Python.
- `apps/mobile`: mobile client shell. Start with the least risky Tauri/iOS prototype, but keep the API clean enough that a SwiftUI client can replace it if Tauri mobile becomes the wrong tool.
- `apps/web`: optional shared web UI package if the Tauri clients use web assets.

The Mac mini owns the production SQLite database. Clients never write directly to SQLite; all writes go through `sfo-server`. This keeps migration, validation, backup, auth, and future concurrency behavior in one place.

## Data Model Strategy

New Rust records should use stable UUID primary identifiers at the API/domain level. Imported Python rows should keep their old integer IDs in nullable `legacy_*_id` columns where useful for verification and rollback. This avoids coupling future client/server behavior to local auto-increment IDs while preserving a clear migration audit path.

Initial schema groups:

- Planning: projects, tasks, blocks, success packs, waiting-on.
- Intake: inbox task fields, intake intent/container, archived inbox state.
- Review: weekly review state, resurfacing, rituals.
- Profile: user profile, app preferences, auth/device tokens.
- Health: metrics, entries, goals, supplements, exercise sessions, training plans, set logs.
- Guidance: reminders, events, coach conversations/messages.
- Integrations: email sync state and imported email messages.
- System: schema migrations, import batches, audit log, backup manifest records.

SQLite remains appropriate for the first server alpha because there is one writer process and one canonical database. The server should enable WAL mode, foreign keys, busy timeout, and predictable backup snapshots.

## API Strategy

The first API should be JSON-only and versioned under `/api/v1`. HTML routes from the Python app become reference behavior, not permanent API design.

First endpoints:

- `GET /healthz`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/bootstrap`
- `GET/POST/PATCH/DELETE /api/v1/projects`
- `GET/POST/PATCH/DELETE /api/v1/tasks`
- `POST /api/v1/inbox/quick-capture`
- `POST /api/v1/inbox/process`
- `POST /api/v1/import/python-sqlite`
- `POST /api/v1/export/backup`

The API should expose use-case operations where the current app has important behavior, such as weekly project caps, task completion timestamps, inbox routing, waiting-on creation, archive/restore semantics, and resurfacing. Simple CRUD is acceptable only where there is no domain behavior.

## Client Strategy

Build the new Mac and iPhone clients together around the same API, but keep the first usable scope narrow:

- App shell, login, connection settings, and server health.
- Dashboard with projects, inbox count, today/week tasks, and waiting-on count.
- Projects and tasks list/detail/edit flows.
- Quick capture and basic inbox processing.
- Backup/export status.

The current visual design can be improved gradually, but the first Rust milestone should favor product correctness over a full visual redesign. The iPhone UI should be designed as a first-class small-screen workflow, not just a compressed desktop layout.

## Auth And Deployment

The Mac mini server should use:

- `axum` for HTTP routing.
- `tower-http` for tracing, CORS, compression, and request limits.
- Argon2 password hashing for the primary user account.
- Secure opaque session/device tokens stored hashed in SQLite.
- Local config through environment variables and a server config file.
- `systemd` for process management on the Mac mini.
- nginx or Caddy as the reverse proxy if TLS or LAN/VPN hostnames are needed.

The first deployment target can stay private-network/VPN only. Public internet exposure should be treated as a separate hardening project.

## Migration Strategy

Migration should be built early, before feature parity, so every slice can be verified against real data shape.

1. Add a Rust importer that opens a copy of the Python SQLite database read-only.
2. Import tables into the new schema in dependency order.
3. Store import batch metadata, row counts, source database checksum, and per-table warnings.
4. Preserve old integer IDs as legacy IDs.
5. Provide a dry-run mode that reports unsupported columns and data anomalies without writing.
6. Compare exported counts and representative records against the Python app tests/fixtures.

No migration tool should operate on the live Python database directly. It should require a copied snapshot or backup export.

## Testing Strategy

Every slice should include tests before implementation work is considered done:

- `sfo-core`: enum serialization, validation, DTO compatibility.
- `sfo-db`: SQLx migration tests, repository tests against temporary SQLite databases.
- `sfo-services`: use-case tests for weekly caps, task mutation behavior, inbox routing, waiting-on creation, completion/archive/reopen semantics.
- `sfo-server`: Axum integration tests for auth, API status codes, pagination, validation errors, and JSON shape.
- Importer: fixture SQLite databases and dry-run/import count assertions.
- Clients: smoke tests for app launch, login flow, and core API calls.

Current Python tests remain useful as behavioral documentation until the equivalent Rust service tests exist.

## Implementation Phases

### Phase 1: Foundation Slice

Create the Rust workspace, core domain types, SQLite migration setup, Axum server shell, `/healthz`, config loading, and test harness. This proves the build, test, and crate boundaries.

### Phase 2: Projects And Tasks

Port projects and tasks with service-level behavior: weekly cap, task status transitions, completion timestamps, archive/reopen, sorting, pagination, and validation. Add API tests before client work depends on the endpoints.

### Phase 3: Basic Clients

Build the Mac and iPhone client shells together: connection settings, login, dashboard, projects, tasks, and quick capture. The UI can be simple but must be usable on desktop and phone.

### Phase 4: Import And Backup

Implement Python SQLite import, dry-run checks, backup export, backup health, and server runbook. This is the gate before using real data as the primary database.

### Phase 5: Inbox And Review Workflows

Port inbox containers, guided processing, resurfacing, weekly review, waiting-on, rituals, and profile/onboarding behavior.

### Phase 6: Health, Coach, And Integrations

Port health tracking, training logs, guidance reminders, coach history/actions, Gmail sync, and any local LLM integration. These should not block the first usable Mac/iPhone rewrite.

## Key Risks

- Full feature parity is large. The rewrite must move by vertical slices with tests and commits, not by one broad scaffold.
- Tauri mobile may or may not be the best long-term iPhone UI. The API should keep that decision reversible.
- The current Python Tauri wrapper requires ignored bundled resources to compile, which is a useful baseline issue but should disappear once Rust owns the server.
- Integer-to-UUID migration must be designed carefully so imported data can be audited.
- Remote access security should remain private-network/VPN until auth, TLS, backup, and rate-limit behavior are intentionally hardened.

## Acceptance Criteria For The First Rewrite Milestone

- A Rust workspace builds with `cargo test --workspace`.
- `/healthz` returns server and database status.
- Projects and tasks can be created, listed, updated, completed, archived, and deleted through `/api/v1`.
- The first client shell can connect to the server and exercise projects/tasks/quick capture on macOS and an iPhone simulator or device.
- A dry-run importer can inspect a Python SFO SQLite snapshot and report table counts and warnings.
- Documentation explains how to run the server locally and where the Mac mini deployment will live.
