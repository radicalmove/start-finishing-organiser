# SFO Rust Projects And Tasks API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first real Rust product slice: projects, tasks, task lifecycle mutations, and quick inbox capture under `/api/v1`.

**Architecture:** Keep domain/API shapes in `sfo-core`, persistence in `sfo-db`, use-case rules in a new `sfo-services` crate, and HTTP concerns in `sfo-server`. Match current Python behavior for weekly project caps, pagination, task completion/archive/reopen/restore, and quick capture state.

**Tech Stack:** Rust 2021, Axum 0.8, SQLx 0.8 SQLite, Serde, UUID v7, Tokio, tower integration tests

---

## File Structure

- Modify: `Cargo.toml`
- Modify: `crates/sfo-core/Cargo.toml`
- Modify: `crates/sfo-core/src/ids.rs`
- Modify: `crates/sfo-core/src/lib.rs`
- Create: `crates/sfo-core/src/planning.rs`
- Modify: `crates/sfo-db/Cargo.toml`
- Modify: `crates/sfo-db/src/lib.rs`
- Create: `crates/sfo-db/src/planning.rs`
- Create: `crates/sfo-db/migrations/0002_projects_tasks.sql`
- Create: `crates/sfo-services/Cargo.toml`
- Create: `crates/sfo-services/src/lib.rs`
- Create: `crates/sfo-services/src/error.rs`
- Create: `crates/sfo-services/src/planning.rs`
- Modify: `crates/sfo-server/Cargo.toml`
- Modify: `crates/sfo-server/src/lib.rs`
- Modify: `crates/sfo-server/src/routes/mod.rs`
- Create: `crates/sfo-server/src/routes/api.rs`
- Create: `crates/sfo-server/tests/projects_tasks_api.rs`
- Modify: `docs/rust_rewrite.md`

## Task 1: Domain Types And IDs

- [ ] Write failing `sfo-core` tests for ID string parsing plus project/task DTO JSON defaults.
- [ ] Run `cargo test -p sfo-core`; expect missing parsing/domain type failures.
- [ ] Add ID `Display`/`FromStr`, planning enums, API request/response structs, and paginated response type.
- [ ] Run `cargo test -p sfo-core`; expect PASS.

## Task 2: SQLite Schema And Repository

- [ ] Add `sfo-core` as a dependency of `sfo-db`.
- [ ] Write failing `sfo-db` tests for project insert/list/update/delete, weekly active counts, task insert/list/update/delete, and migration creation.
- [ ] Run `cargo test -p sfo-db`; expect missing repository/schema failures.
- [ ] Add `0002_projects_tasks.sql` and repository functions in `crates/sfo-db/src/planning.rs`.
- [ ] Run `cargo test -p sfo-db`; expect PASS.

## Task 3: Services

- [ ] Add `sfo-services` to the workspace.
- [ ] Write failing service tests for work weekly cap, personal weekly cap, task complete/reopen/archive/restore, and quick capture defaults.
- [ ] Run `cargo test -p sfo-services`; expect missing implementation failures.
- [ ] Implement `PlanningService` and map repository/database errors to service errors.
- [ ] Run `cargo test -p sfo-services`; expect PASS.

## Task 4: HTTP API

- [ ] Add failing Axum integration tests for:
  - `POST/GET/PATCH/DELETE /api/v1/projects`
  - weekly cap error returns `400`
  - `POST/GET/PATCH/DELETE /api/v1/tasks`
  - `POST /api/v1/tasks/{id}/complete`
  - `POST /api/v1/tasks/{id}/reopen`
  - `POST /api/v1/tasks/{id}/archive`
  - `POST /api/v1/tasks/{id}/restore`
  - `POST /api/v1/inbox/quick-capture`
- [ ] Run `cargo test -p sfo-server --test projects_tasks_api`; expect missing route failures.
- [ ] Add `routes/api.rs`, mount `/api/v1`, and translate service errors into JSON HTTP responses.
- [ ] Run `cargo test -p sfo-server --test projects_tasks_api`; expect PASS.

## Task 5: Documentation And Verification

- [ ] Update `docs/rust_rewrite.md` with the new API endpoints.
- [ ] Run `cargo fmt --all --check`.
- [ ] Run `cargo test --workspace`.
- [ ] Run `.venv/bin/python -m pytest`.
- [ ] Run `cargo check --manifest-path src-tauri/Cargo.toml`.
- [ ] Run `git diff --check`.
- [ ] Review `git diff --stat` and commit as `feat: add rust projects tasks api`.
