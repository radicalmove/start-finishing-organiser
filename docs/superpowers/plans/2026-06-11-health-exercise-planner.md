# Health Exercise Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Health plugin feature: weekly exercise planning with structured gym, cardio, and flexibility session details across Mac and iPhone.

**Architecture:** Health exercise data lives in normal Rust SFO-owned SQLite tables so it backs up with the main database. The feature is exposed through plugin-scoped `/api/v1/plugins/health/exercise/*` routes and rendered inside the existing launcher plugin surfaces without adding a sixth top-level tab.

**Tech Stack:** Rust workspace (`sfo-core`, `sfo-db`, `sfo-services`, `sfo-server`), SQLx SQLite migrations, Axum API, vanilla launcher JS/CSS, Node test runner.

---

## Spec Reference

- `docs/superpowers/specs/2026-06-11-health-exercise-planner-design.md`

## File Structure

- Create `crates/sfo-core/src/health.rs`: Health exercise IDs, enums, DTOs, create/update/status request types, and serialization tests.
- Modify `crates/sfo-core/src/lib.rs`: export Health types.
- Create `crates/sfo-db/migrations/0009_health_exercise_planner.sql`: session and typed detail tables.
- Create `crates/sfo-db/src/health.rs`: repository functions for CRUD, week loading, status update, and transactional detail replacement.
- Modify `crates/sfo-db/src/lib.rs`: expose Health repository module.
- Modify `crates/sfo-db/src/backup.rs`: include Health exercise tables in manifest and snapshot copying.
- Create `crates/sfo-services/src/health.rs`: validation, Health plugin write guard, week normalization, and service orchestration.
- Modify `crates/sfo-services/src/lib.rs`: expose `HealthService`.
- Modify `crates/sfo-server/src/routes/api.rs`: add Health exercise API routes under `/plugins/health/exercise`.
- Create `crates/sfo-server/tests/health_exercise_api.rs`: API coverage.
- Modify `docs/rust_rewrite.md`: document the new Health exercise routes and backup behavior.
- Modify `src-tauri/launcher/client.js`: Health exercise API path helpers, view models, and payload builders.
- Modify `src-tauri/launcher/client.test.mjs`: Health exercise client tests.
- Modify `src-tauri/launcher/index.html`: Health exercise containers inside Review/Settings plugin area.
- Modify `src-tauri/launcher/launcher.js`: load/render Health exercise week, create/update/status/delete handlers.
- Modify `src-tauri/launcher/launcher.css`: compact Health exercise cards and iPhone SE layout.
- Modify `src-tauri/launcher/workflow-shell.test.mjs` and `src-tauri/launcher/mobile-shell.test.mjs`: static/mobile coverage.

## Task 1: Core Health Exercise Types

**Files:**
- Create: `crates/sfo-core/src/health.rs`
- Modify: `crates/sfo-core/src/lib.rs`

- [ ] **Step 1: Write failing core serialization tests**

Add tests for:

- `HealthExerciseWeek` serializes `week_start`, `week_end`, and session list.
- `HealthExerciseSession` serializes `session_type`, `status`, and typed detail rows.
- `HealthExerciseSessionCreate` defaults status to `planned`.

Run:

```bash
cargo test -p sfo-core health
```

Expected: FAIL because the Health module/types do not exist.

- [ ] **Step 2: Implement core types**

Create focused types:

- `HealthExerciseSessionId`
- `HealthExerciseSessionType`: `Gym`, `Cardio`, `Flexibility`
- `HealthExerciseSessionStatus`: `Planned`, `Done`, `Skipped`
- `HealthGymExercise`
- `HealthCardioExercise`
- `HealthFlexibilityExercise`
- `HealthExerciseDetails`
- `HealthExerciseSession`
- `HealthExerciseWeek`
- `HealthExerciseSessionCreate`
- `HealthExerciseSessionUpdate`
- `HealthExerciseStatusUpdate`

Use `serde(rename_all = "snake_case")` for enums and string id behavior consistent with plugin IDs.

- [ ] **Step 3: Export the module**

Modify `crates/sfo-core/src/lib.rs`:

```rust
pub mod health;
pub use health::*;
```

- [ ] **Step 4: Verify and commit**

Run:

```bash
cargo test -p sfo-core health
```

Commit:

```bash
git add crates/sfo-core/src/health.rs crates/sfo-core/src/lib.rs
git commit -m "Add health exercise core types"
```

## Task 2: Database Migration And Repository

**Files:**
- Create: `crates/sfo-db/migrations/0009_health_exercise_planner.sql`
- Create: `crates/sfo-db/src/health.rs`
- Modify: `crates/sfo-db/src/lib.rs`

- [ ] **Step 1: Write failing DB tests**

Add tests in `crates/sfo-db/src/health.rs` for:

- Creating a gym session with exercise rows.
- Loading a week with sessions between Monday and Sunday.
- Updating a session replaces detail rows transactionally.
- Status update changes only status/updated timestamp.
- Deleting a session cascades detail rows.

Run:

```bash
cargo test -p sfo-db health
```

Expected: FAIL because migration/repository do not exist.

- [ ] **Step 2: Add migration**

Create tables:

- `health_exercise_sessions`
- `health_gym_exercises`
- `health_cardio_exercises`
- `health_flexibility_exercises`

Include:

- text IDs as primary keys.
- `session_date`, `session_type`, `title`, `target_duration_minutes`, `status`, `notes`, `created_at`, `updated_at`.
- typed detail rows with `session_id`, `position`, fields from the spec, and cascade delete.
- indexes on `session_date`, `session_type`, and `session_id`.

- [ ] **Step 3: Implement repository**

Functions:

- `create_session(pool, HealthExerciseSessionCreate) -> HealthExerciseSession`
- `get_session(pool, &HealthExerciseSessionId) -> Option<HealthExerciseSession>`
- `list_week(pool, week_start: NaiveDate) -> Vec<HealthExerciseSession>`
- `update_session(pool, &HealthExerciseSessionId, HealthExerciseSessionUpdate) -> HealthExerciseSession`
- `update_session_status(pool, &HealthExerciseSessionId, HealthExerciseSessionStatus) -> HealthExerciseSession`
- `delete_session(pool, &HealthExerciseSessionId) -> ()`

Keep detail replacement inside one transaction.

- [ ] **Step 4: Export repository module**

Modify `crates/sfo-db/src/lib.rs`:

```rust
pub mod health;
```

- [ ] **Step 5: Verify and commit**

Run:

```bash
cargo test -p sfo-db health
```

Commit:

```bash
git add crates/sfo-db/migrations/0009_health_exercise_planner.sql crates/sfo-db/src/health.rs crates/sfo-db/src/lib.rs
git commit -m "Add health exercise database support"
```

## Task 3: Service Layer

**Files:**
- Create: `crates/sfo-services/src/health.rs`
- Modify: `crates/sfo-services/src/lib.rs`

- [ ] **Step 1: Write failing service tests**

Add tests for:

- Disabled Health plugin rejects create/update/status/delete writes.
- Enabled Health plugin allows writes.
- Week input normalizes to Monday.
- Blank optional text normalizes to `None`.
- Zero/negative numeric values are rejected.

Run:

```bash
cargo test -p sfo-services health
```

Expected: FAIL because `HealthService` does not exist.

- [ ] **Step 2: Implement service**

Create `HealthService` with:

- `exercise_week(date: NaiveDate) -> HealthExerciseWeek`
- `create_exercise_session(payload) -> HealthExerciseSession`
- `get_exercise_session(id) -> HealthExerciseSession`
- `update_exercise_session(id, payload) -> HealthExerciseSession`
- `update_exercise_session_status(id, payload) -> HealthExerciseSession`
- `delete_exercise_session(id) -> ()`

Use `PluginService` or `sfo_db::plugins` to seed and check `health` enabled for writes. Reads should seed plugins but not require enabled state.

- [ ] **Step 3: Export service**

Modify `crates/sfo-services/src/lib.rs`:

```rust
pub mod health;
pub use health::HealthService;
```

- [ ] **Step 4: Verify and commit**

Run:

```bash
cargo test -p sfo-services health
```

Commit:

```bash
git add crates/sfo-services/src/health.rs crates/sfo-services/src/lib.rs
git commit -m "Add health exercise service rules"
```

## Task 4: API Routes

**Files:**
- Modify: `crates/sfo-server/src/routes/api.rs`
- Create: `crates/sfo-server/tests/health_exercise_api.rs`

- [ ] **Step 1: Write failing API tests**

Test:

- `GET /api/v1/plugins/health/exercise/weeks/2026-06-10` normalizes to Monday and returns an empty week.
- Enabling Health then `POST /sessions` creates a structured gym/cardio/flexibility session.
- `GET /sessions/{id}` fetches details.
- `PUT /sessions/{id}` replaces details.
- `POST /sessions/{id}/status` marks done/skipped.
- `DELETE /sessions/{id}` removes the session.
- Existing token auth protects all routes.

Run:

```bash
cargo test -p sfo-server --test health_exercise_api
```

Expected: FAIL with `404` before routes exist.

- [ ] **Step 2: Implement route handlers**

Add routes under `/api/v1`:

- `/plugins/health/exercise/weeks/{week_start}`
- `/plugins/health/exercise/sessions`
- `/plugins/health/exercise/sessions/{session_id}`
- `/plugins/health/exercise/sessions/{session_id}/status`

Use `HealthService` and existing `ApiError` conversion.

- [ ] **Step 3: Verify and commit**

Run:

```bash
cargo test -p sfo-server --test health_exercise_api
cargo test -p sfo-server --test auth_api
```

Commit:

```bash
git add crates/sfo-server/src/routes/api.rs crates/sfo-server/tests/health_exercise_api.rs
git commit -m "Expose health exercise API"
```

## Task 5: Backup And Docs

**Files:**
- Modify: `crates/sfo-db/src/backup.rs`
- Modify: `docs/rust_rewrite.md`

- [ ] **Step 1: Write failing backup assertions**

Extend backup tests to seed Health exercise rows and assert:

- Manifest includes all Health exercise tables.
- SQLite snapshot copies sessions and typed details.

Run:

```bash
cargo test -p sfo-db backup
```

Expected: FAIL until backup includes the new tables.

- [ ] **Step 2: Add backup copy support**

Add tables to `RUST_BACKUP_TABLES`, read rows from all Health exercise tables, delete/insert them in foreign-key-safe order.

- [ ] **Step 3: Update docs**

Document:

- Health exercise API routes.
- Health plugin write behavior.
- Backup preservation for Health exercise tables.

- [ ] **Step 4: Verify and commit**

Run:

```bash
cargo test -p sfo-db backup
```

Commit:

```bash
git add crates/sfo-db/src/backup.rs docs/rust_rewrite.md
git commit -m "Preserve health exercise data in backups"
```

## Task 6: Launcher Client Models

**Files:**
- Modify: `src-tauri/launcher/client.js`
- Modify: `src-tauri/launcher/client.test.mjs`

- [ ] **Step 1: Write failing client tests**

Add tests for:

- Health exercise API path builders.
- Week view model groups sessions by day.
- Payload builder trims title/notes and preserves typed rows.
- Status action path builder.

Run:

```bash
node --test src-tauri/launcher/client.test.mjs
```

Expected: FAIL because helpers do not exist.

- [ ] **Step 2: Implement helpers**

Add:

- `buildHealthExerciseWeekPath(date)`
- `buildHealthExerciseSessionPath(sessionId)`
- `buildHealthExerciseStatusPath(sessionId)`
- `buildHealthExerciseWeekViewModel(payload)`
- `buildHealthExerciseSessionPayload(values)`
- `buildHealthExerciseStatusPayload(status)`

- [ ] **Step 3: Verify and commit**

Run:

```bash
node --test src-tauri/launcher/client.test.mjs
```

Commit:

```bash
git add src-tauri/launcher/client.js src-tauri/launcher/client.test.mjs
git commit -m "Add health exercise launcher models"
```

## Task 7: Launcher UI

**Files:**
- Modify: `src-tauri/launcher/index.html`
- Modify: `src-tauri/launcher/launcher.js`
- Modify: `src-tauri/launcher/launcher.css`
- Modify: `src-tauri/launcher/workflow-shell.test.mjs`
- Modify: `src-tauri/launcher/mobile-shell.test.mjs`

- [ ] **Step 1: Write failing static/mobile tests**

Assert:

- Health exercise containers exist.
- Launcher loads `/api/v1/plugins/health/exercise/weeks`.
- No new top-level workflow tab is added.
- Mobile CSS contains iPhone SE treatment for Health exercise cards/forms.

Run:

```bash
node --test src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs
```

Expected: FAIL until UI exists.

- [ ] **Step 2: Add HTML containers**

Add a Health Exercise panel under existing plugin/Review or Settings area with:

- week heading
- previous/next controls
- session list
- add/edit form

- [ ] **Step 3: Wire JS**

Load Health exercise week during plugin refresh, render day groups, submit create/update/status/delete actions through existing `requestJson`.

- [ ] **Step 4: Add CSS**

Use existing visual system:

- subtle radii
- compact iPhone controls
- full-width form rows on small screens
- no new top nav

- [ ] **Step 5: Verify and commit**

Run:

```bash
node --test src-tauri/launcher/client.test.mjs src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs
```

Commit:

```bash
git add src-tauri/launcher/index.html src-tauri/launcher/launcher.js src-tauri/launcher/launcher.css src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs
git commit -m "Surface health exercise planner in launcher"
```

## Task 8: Final Verification And Publish

**Files:**
- All touched files.

- [ ] **Step 1: Run full verification**

Run:

```bash
cargo fmt --all --check
cargo test --workspace
node --test src-tauri/launcher/client.test.mjs src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs
git diff --check
```

For Tauri check in this nested worktree, use a temporary standalone copy or another verified approach that avoids Cargo resolving the parent `/Users/rcd58/sfo` workspace:

```bash
tmpdir=$(mktemp -d /Users/rcd58/sfo-tauri-check-XXXXXX)
cp -R src-tauri "$tmpdir/src-tauri"
CARGO_TARGET_DIR="$PWD/target-tauri-check" cargo check --manifest-path "$tmpdir/src-tauri/Cargo.toml"
result=$?
rm -rf "$tmpdir" target-tauri-check
exit $result
```

- [ ] **Step 2: Fix failures**

If any command fails, fix and rerun the relevant command before continuing.

- [ ] **Step 3: Publish or merge**

Follow the finishing-a-development-branch workflow. Default recommendation is a draft PR because this is a substantial feature slice.
