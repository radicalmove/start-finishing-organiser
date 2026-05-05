# SFO Rust Import And Backup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first Rust data-safety slice: dry-run inspection of a copied Python SFO SQLite database and a backup manifest for the Rust database.

**Architecture:** Add shared import/backup DTOs in `sfo-core`, source database inspection and Rust DB manifest functions in `sfo-db`, service orchestration in `sfo-services`, and JSON endpoints in `sfo-server`. This slice does not mutate imported data yet; it proves file access, table detection, row counts, checksums, and API shape before real migration logic is added.

**Tech Stack:** Rust 2021, SQLx SQLite, Axum, Serde, SHA-256, Tokio

---

## File Structure

- Modify: `Cargo.toml`
- Modify: `crates/sfo-core/src/lib.rs`
- Create: `crates/sfo-core/src/system.rs`
- Modify: `crates/sfo-db/Cargo.toml`
- Modify: `crates/sfo-db/src/lib.rs`
- Create: `crates/sfo-db/src/import.rs`
- Create: `crates/sfo-db/src/backup.rs`
- Modify: `crates/sfo-services/src/lib.rs`
- Create: `crates/sfo-services/src/system.rs`
- Modify: `crates/sfo-server/src/routes/api.rs`
- Create: `crates/sfo-server/tests/import_backup_api.rs`
- Modify: `docs/rust_rewrite.md`

## Task 1: Core DTOs

- [ ] Write tests for `ImportDryRunRequest`, `ImportDryRunReport`, `BackupManifest`, and table count serialization.
- [ ] Run `cargo test -p sfo-core system::tests`; expect missing module/type failures.
- [ ] Implement `crates/sfo-core/src/system.rs` and export it.
- [ ] Run `cargo test -p sfo-core system::tests`; expect PASS.

## Task 2: DB Inspection And Backup Manifest

- [ ] Add `sha2` workspace dependency and `sfo-db` dependency.
- [ ] Write failing DB tests that create temporary SQLite fixture files with Python-like `projects`, `tasks`, `health_entries`, and unknown tables.
- [ ] Assert dry-run reports source checksum, supported table counts, unsupported-table warnings, and missing-table warnings.
- [ ] Assert backup manifest reports counts for Rust `projects`, `tasks`, and `app_metadata`.
- [ ] Run `cargo test -p sfo-db import::tests backup::tests`; expect missing functions.
- [ ] Implement read-only source inspection and Rust DB table counting.
- [ ] Run `cargo test -p sfo-db import::tests backup::tests`; expect PASS.

## Task 3: Services

- [ ] Add `SystemService` in `sfo-services`.
- [ ] Write failing service tests for dry-run import and backup manifest delegation.
- [ ] Run `cargo test -p sfo-services system::tests`; expect missing service failures.
- [ ] Implement service functions and path validation.
- [ ] Run `cargo test -p sfo-services system::tests`; expect PASS.

## Task 4: HTTP Endpoints

- [ ] Add failing Axum integration tests for:
  - `POST /api/v1/import/python-sqlite/dry-run`
  - `POST /api/v1/export/backup`
- [ ] Run `cargo test -p sfo-server --test import_backup_api`; expect missing routes.
- [ ] Add the endpoints to `routes/api.rs` and map errors to JSON responses.
- [ ] Run `cargo test -p sfo-server --test import_backup_api`; expect PASS.

## Task 5: Verification And Commit

- [ ] Update `docs/rust_rewrite.md`.
- [ ] Run `cargo fmt --all --check`.
- [ ] Run `git diff --check`.
- [ ] Run `cargo test --workspace`.
- [ ] Run `.venv/bin/python -m pytest`.
- [ ] Run `cargo check --manifest-path src-tauri/Cargo.toml`.
- [ ] Commit as `feat: add rust import backup dry run`.
