# SFO Plugin Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first safe plugin-platform slice: plugin registry, capabilities, reviewable suggestions, API routes, backup support, and minimal launcher UI.

**Architecture:** Plugins are first-party/server-side records in this slice, not dynamically loaded code. The platform adds typed core DTOs, SQLite tables, DB repositories, service-layer validation, Axum routes, and static launcher views. Plugin suggestions are reviewable; approval converts only supported suggestion kinds through normal SFO service rules.

**Tech Stack:** Rust workspace (`sfo-core`, `sfo-db`, `sfo-services`, `sfo-server`), SQLite migrations via SQLx, Axum API, vanilla JS/CSS launcher tests with Node test runner.

---

## Spec Reference

- Design: `docs/superpowers/specs/2026-06-03-sfo-plugin-platform-design.md`

## File Structure

- Create `crates/sfo-core/src/plugins.rs`: plugin DTOs, enums, create/update request types, suggestion approval/dismissal types.
- Modify `crates/sfo-core/src/lib.rs`: export plugin types.
- Create `crates/sfo-db/migrations/0008_plugin_platform.sql`: plugin registry, capabilities, suggestions.
- Create `crates/sfo-db/src/plugins.rs`: repository functions for registry, capabilities, suggestions, lifecycle updates, seed rows.
- Modify `crates/sfo-db/src/lib.rs`: expose plugin repository module.
- Modify `crates/sfo-db/src/backup.rs`: include plugin tables in backup manifest/copy.
- Create `crates/sfo-services/src/plugins.rs`: service rules, disabled-plugin guard, approval conversion, seed registration helper.
- Modify `crates/sfo-services/src/lib.rs`: expose plugin service.
- Modify `crates/sfo-server/src/routes/api.rs`: add `/api/v1/plugins` routes.
- Add API tests in `crates/sfo-server/tests/plugins_api.rs`.
- Add DB/service tests near new modules, following current crate test style.
- Modify `src-tauri/launcher/client.js`: plugin API path helpers and plugin view-model builders.
- Modify `src-tauri/launcher/launcher.js`: load plugin data on connect/refresh and render Settings/Review surfaces.
- Modify `src-tauri/launcher/index.html`: add Settings plugin container and Review suggestions container.
- Modify `src-tauri/launcher/launcher.css`: minimal plugin cards and suggestion queue styling, including iPhone SE layout.
- Modify `src-tauri/launcher/client.test.mjs`, `workflow-shell.test.mjs`, and `mobile-shell.test.mjs`: launcher coverage.
- Modify `docs/rust_rewrite.md`: document plugin-platform API and behavior.

## Data Contracts

Use these enum string values unless implementation uncovers an existing naming pattern that should be followed instead:

```rust
PluginTrustLevel: "first_party" | "local_private" | "external_sidecar"
PluginStatus: "not_configured" | "ready" | "degraded" | "disabled"
PluginCapabilityKind:
  "read_sfo_context"
  "create_suggestions"
  "create_tasks"
  "create_waiting_items"
  "health_read"
  "health_write"
  "communications_read_metadata"
  "communications_read_content"
  "communications_create_drafts"
  "calendar_read"
  "calendar_suggest_blocks"
PluginSuggestionKind: "task" | "waiting" | "draft_message" | "health_prompt" | "calendar_block" | "generic"
PluginSuggestionPriority: "low" | "normal" | "high"
PluginSuggestionStatus: "pending" | "approved" | "dismissed" | "superseded" | "failed"
```

Seed disabled first-party plugins:

```text
health
communications
```

---

### Task 1: Core Plugin Types

**Files:**
- Create: `crates/sfo-core/src/plugins.rs`
- Modify: `crates/sfo-core/src/lib.rs`

- [ ] **Step 1: Write failing DTO serialization tests**

Add tests in `crates/sfo-core/src/plugins.rs` behind `#[cfg(test)]`:

```rust
#[test]
fn plugin_summary_serializes_capabilities_and_status() {
    let plugin = PluginSummary {
        id: PluginId::from("health"),
        name: "Health".to_string(),
        description: Some("Exercise and diet tracking".to_string()),
        version: "0.1.0".to_string(),
        enabled: false,
        trust_level: PluginTrustLevel::FirstParty,
        status: PluginStatus::Disabled,
        status_detail: Some("Disabled until configured".to_string()),
        capabilities: vec![PluginCapability {
            id: PluginCapabilityId::from("cap-1"),
            plugin_id: PluginId::from("health"),
            capability: PluginCapabilityKind::HealthRead,
            enabled: false,
        }],
    };

    let json = serde_json::to_value(plugin).expect("serialize plugin");
    assert_eq!(json["id"], "health");
    assert_eq!(json["trust_level"], "first_party");
    assert_eq!(json["status"], "disabled");
    assert_eq!(json["capabilities"][0]["capability"], "health_read");
}

#[test]
fn plugin_suggestion_serializes_review_queue_contract() {
    let suggestion = PluginSuggestion {
        id: PluginSuggestionId::from("suggestion-1"),
        plugin_id: PluginId::from("communications"),
        kind: PluginSuggestionKind::Waiting,
        title: "Follow up with Alex".to_string(),
        summary: Some("Teams thread needs a response".to_string()),
        detail: None,
        payload_json: serde_json::json!({"description": "Follow up with Alex"}),
        source_label: Some("Teams".to_string()),
        source_uri: None,
        confidence: Some(0.82),
        priority: PluginSuggestionPriority::High,
        status: PluginSuggestionStatus::Pending,
        created_core_kind: None,
        created_core_id: None,
        created_at: chrono::Utc::now(),
        updated_at: chrono::Utc::now(),
        resolved_at: None,
    };

    let json = serde_json::to_value(suggestion).expect("serialize suggestion");
    assert_eq!(json["kind"], "waiting");
    assert_eq!(json["priority"], "high");
    assert_eq!(json["status"], "pending");
}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p sfo-core plugins`

Expected: FAIL because plugin types/module do not exist.

- [ ] **Step 3: Implement core DTOs**

Create focused types:

```rust
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::ids::string_id;

string_id!(PluginId);
string_id!(PluginCapabilityId);
string_id!(PluginSuggestionId);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PluginTrustLevel { FirstParty, LocalPrivate, ExternalSidecar }

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PluginStatus { NotConfigured, Ready, Degraded, Disabled }

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PluginCapabilityKind {
    ReadSfoContext,
    CreateSuggestions,
    CreateTasks,
    CreateWaitingItems,
    HealthRead,
    HealthWrite,
    CommunicationsReadMetadata,
    CommunicationsReadContent,
    CommunicationsCreateDrafts,
    CalendarRead,
    CalendarSuggestBlocks,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PluginSuggestionKind { Task, Waiting, DraftMessage, HealthPrompt, CalendarBlock, Generic }

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PluginSuggestionPriority { Low, Normal, High }

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PluginSuggestionStatus { Pending, Approved, Dismissed, Superseded, Failed }
```

Add structs:

- `PluginCapability`
- `PluginSummary`
- `PluginDetail`
- `PluginUpdate`
- `PluginSuggestion`
- `PluginSuggestionCreate`
- `PluginSuggestionApproval`
- `PluginSuggestionDismissal`

Use existing crate patterns for optional fields and `serde_json::Value`.

- [ ] **Step 4: Export the module**

Modify `crates/sfo-core/src/lib.rs`:

```rust
pub mod plugins;
pub use plugins::*;
```

- [ ] **Step 5: Run tests**

Run: `cargo test -p sfo-core plugins`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crates/sfo-core/src/lib.rs crates/sfo-core/src/plugins.rs
git commit -m "Add plugin platform core types"
```

---

### Task 2: Database Migration and Repository

**Files:**
- Create: `crates/sfo-db/migrations/0008_plugin_platform.sql`
- Create: `crates/sfo-db/src/plugins.rs`
- Modify: `crates/sfo-db/src/lib.rs`

- [ ] **Step 1: Write failing DB tests**

In `crates/sfo-db/src/plugins.rs`, add tests for:

- migration creates tables
- seed registers disabled `health` and `communications`
- capability enable/disable persists
- suggestion create/list/detail/update persists

Test shape:

```rust
#[tokio::test]
async fn seed_plugins_registers_disabled_first_party_plugins() {
    let pool = crate::connect(&crate::DbConfig::memory()).await.expect("db");
    seed_builtin_plugins(&pool).await.expect("seed plugins");

    let plugins = list_plugins(&pool).await.expect("plugins");
    assert!(plugins.iter().any(|plugin| plugin.id.as_str() == "health"));
    assert!(plugins.iter().any(|plugin| plugin.id.as_str() == "communications"));
    assert!(plugins.iter().all(|plugin| !plugin.enabled));
}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p sfo-db plugins`

Expected: FAIL because migration/repository functions do not exist.

- [ ] **Step 3: Add migration**

Create SQL tables:

```sql
CREATE TABLE plugins (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NULL,
  version TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 0,
  trust_level TEXT NOT NULL,
  status TEXT NOT NULL,
  status_detail TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE plugin_capabilities (
  id TEXT PRIMARY KEY,
  plugin_id TEXT NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
  capability TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
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
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  resolved_at TEXT NULL
);

CREATE INDEX idx_plugin_capabilities_plugin_id ON plugin_capabilities(plugin_id);
CREATE INDEX idx_plugin_suggestions_status_created ON plugin_suggestions(status, created_at);
CREATE INDEX idx_plugin_suggestions_plugin_status ON plugin_suggestions(plugin_id, status);
```

- [ ] **Step 4: Implement repository**

Implement focused functions:

- `seed_builtin_plugins(pool)`
- `list_plugins(pool)`
- `get_plugin(pool, plugin_id)`
- `update_plugin(pool, plugin_id, update)`
- `set_capability_enabled(pool, plugin_id, capability, enabled)`
- `create_suggestion(pool, create)`
- `list_suggestions(pool, statuses)`
- `get_suggestion(pool, suggestion_id)`
- `mark_suggestion_approved(pool, suggestion_id, created_core_kind, created_core_id)`
- `mark_suggestion_dismissed(pool, suggestion_id)`
- `mark_suggestion_failed(pool, suggestion_id, detail)`

Use existing parse helpers and row-mapping style from `planning.rs`, `waiting.rs`, and `search.rs`.

- [ ] **Step 5: Export repository module**

Modify `crates/sfo-db/src/lib.rs`:

```rust
pub mod plugins;
```

- [ ] **Step 6: Run DB tests**

Run: `cargo test -p sfo-db plugins`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add crates/sfo-db/migrations/0008_plugin_platform.sql crates/sfo-db/src/lib.rs crates/sfo-db/src/plugins.rs
git commit -m "Add plugin registry database support"
```

---

### Task 3: Service Layer Rules

**Files:**
- Create: `crates/sfo-services/src/plugins.rs`
- Modify: `crates/sfo-services/src/lib.rs`

- [ ] **Step 1: Write failing service tests**

Add tests for:

- disabled plugin cannot create a suggestion
- enabled plugin can create a pending suggestion
- dismissing a suggestion does not create core data
- approving a `task` suggestion creates a task through `PlanningService`
- approving a `waiting` suggestion creates a Waiting On item through `WaitingService`
- approving a `calendar_block` suggestion creates a block through `ScheduleService`
- unsupported approval payload fails cleanly

Example:

```rust
#[tokio::test]
async fn disabled_plugin_cannot_create_suggestions() {
    let pool = test_pool().await;
    let service = PluginService::new(pool.clone());
    service.seed_builtin_plugins().await.expect("seed");

    let err = service
        .create_suggestion(PluginSuggestionCreate {
            plugin_id: PluginId::from("health"),
            kind: PluginSuggestionKind::HealthPrompt,
            title: "Log weight".to_string(),
            summary: None,
            detail: None,
            payload_json: serde_json::json!({}),
            source_label: Some("Health".to_string()),
            source_uri: None,
            confidence: None,
            priority: PluginSuggestionPriority::Normal,
        })
        .await
        .expect_err("disabled plugin should fail");

    assert!(matches!(err, ServiceError::Validation { .. }));
}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p sfo-services plugins`

Expected: FAIL because `PluginService` does not exist.

- [ ] **Step 3: Implement service**

Implement `PluginService` with:

- `new(db)`
- `seed_builtin_plugins()`
- `list_plugins()`
- `get_plugin(plugin_id)`
- `update_plugin(plugin_id, update)`
- `create_suggestion(create)`
- `list_suggestions()`
- `get_suggestion(suggestion_id)`
- `approve_suggestion(suggestion_id)`
- `dismiss_suggestion(suggestion_id)`

Approval rules:

- `PluginSuggestionKind::Task`: parse `payload_json` into a minimal task create payload and call existing planning service/repository path.
- `PluginSuggestionKind::Waiting`: parse into `WaitingOnCreate` and call `WaitingService`.
- `PluginSuggestionKind::CalendarBlock`: parse into `BlockCreate` and call `ScheduleService`.
- `PluginSuggestionKind::DraftMessage`, `HealthPrompt`, `Generic`: mark as approved but do not create a core object yet.
- Any malformed payload returns `ServiceError::Validation`.

- [ ] **Step 4: Export service module**

Modify `crates/sfo-services/src/lib.rs`:

```rust
pub mod plugins;
pub use plugins::PluginService;
```

- [ ] **Step 5: Run service tests**

Run: `cargo test -p sfo-services plugins`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crates/sfo-services/src/lib.rs crates/sfo-services/src/plugins.rs
git commit -m "Add plugin suggestion service rules"
```

---

### Task 4: Plugin API Routes

**Files:**
- Modify: `crates/sfo-server/src/routes/api.rs`
- Create: `crates/sfo-server/tests/plugins_api.rs`

- [ ] **Step 1: Write failing API tests**

Create tests for:

- `GET /api/v1/plugins`
- `PATCH /api/v1/plugins/health`
- `GET /api/v1/plugins/suggestions`
- `POST /api/v1/plugins/suggestions/{id}/approve`
- `POST /api/v1/plugins/suggestions/{id}/dismiss`
- auth protects plugin routes

Use patterns from `search_api.rs`, `waiting_api.rs`, and `auth_api.rs`.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p sfo-server plugins_api`

Expected: FAIL because routes do not exist.

- [ ] **Step 3: Add routes**

Add to `router()`:

```rust
.route("/plugins", get(list_plugins))
.route("/plugins/{plugin_id}", get(get_plugin).patch(update_plugin))
.route("/plugins/suggestions", get(list_plugin_suggestions))
.route("/plugins/suggestions/{suggestion_id}", get(get_plugin_suggestion))
.route("/plugins/suggestions/{suggestion_id}/approve", post(approve_plugin_suggestion))
.route("/plugins/suggestions/{suggestion_id}/dismiss", post(dismiss_plugin_suggestion))
```

Add handlers that instantiate `PluginService::new(state.db)`.

- [ ] **Step 4: Ensure seed registration happens**

Prefer explicit seed in server startup or first plugin route call. If startup seeding is cleaner, modify server setup so `PluginService::seed_builtin_plugins()` runs after migrations and before serving. Keep it idempotent.

- [ ] **Step 5: Run API tests**

Run: `cargo test -p sfo-server plugins_api`

Expected: PASS.

- [ ] **Step 6: Run auth regression**

Run: `cargo test -p sfo-server auth_api`

Expected: PASS and plugin routes require auth when token is configured.

- [ ] **Step 7: Commit**

```bash
git add crates/sfo-server/src/routes/api.rs crates/sfo-server/tests/plugins_api.rs
git commit -m "Expose plugin platform API"
```

---

### Task 5: Backup and Docs

**Files:**
- Modify: `crates/sfo-db/src/backup.rs`
- Modify: `docs/rust_rewrite.md`

- [ ] **Step 1: Write failing backup test**

Add or extend a backup test so plugin tables appear in the manifest counts and copied backup.

Expected assertion:

```rust
assert!(manifest.tables.iter().any(|table| table.name == "plugins"));
assert!(manifest.tables.iter().any(|table| table.name == "plugin_capabilities"));
assert!(manifest.tables.iter().any(|table| table.name == "plugin_suggestions"));
```

- [ ] **Step 2: Run test to verify failure**

Run: `cargo test -p sfo-db backup`

Expected: FAIL because backup does not include plugin tables yet.

- [ ] **Step 3: Add plugin tables to backup support**

Update table copy/count lists in `backup.rs` to include:

- `plugins`
- `plugin_capabilities`
- `plugin_suggestions`

- [ ] **Step 4: Update docs**

In `docs/rust_rewrite.md`, add:

- current plugin API routes
- plugin registry/suggestion behavior
- Health and Communications as disabled first-party plugin seeds
- note that Health and Communications functionality is follow-on work

- [ ] **Step 5: Run tests**

Run: `cargo test -p sfo-db backup`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crates/sfo-db/src/backup.rs docs/rust_rewrite.md
git commit -m "Include plugin platform in backups"
```

---

### Task 6: Launcher Client Helpers

**Files:**
- Modify: `src-tauri/launcher/client.js`
- Modify: `src-tauri/launcher/client.test.mjs`

- [ ] **Step 1: Write failing client tests**

Add tests for:

- plugin suggestions path builder
- plugin registry view model groups enabled/disabled/status
- suggestion queue view model groups high-priority pending suggestions first
- capability labels are user-readable

Example:

```js
test("plugin view model explains capabilities in plain language", () => {
  const model = buildPluginRegistryViewModel([
    {
      id: "communications",
      name: "Communications",
      enabled: false,
      status: "disabled",
      capabilities: [{ capability: "communications_create_drafts", enabled: false }],
    },
  ]);

  assert.equal(model.plugins[0].capabilities[0].label, "Create draft replies");
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `node --test src-tauri/launcher/client.test.mjs`

Expected: FAIL because helper functions do not exist.

- [ ] **Step 3: Implement helpers**

Add:

- `buildPluginsApiPath()`
- `buildPluginApiPath(pluginId)`
- `buildPluginSuggestionsApiPath()`
- `buildPluginSuggestionActionApiPath(suggestionId, action)`
- `buildPluginRegistryViewModel(plugins)`
- `buildPluginSuggestionsViewModel(suggestions)`
- `pluginCapabilityLabel(capability)`

- [ ] **Step 4: Run tests**

Run: `node --test src-tauri/launcher/client.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src-tauri/launcher/client.js src-tauri/launcher/client.test.mjs
git commit -m "Add launcher plugin view models"
```

---

### Task 7: Launcher UI Surfaces

**Files:**
- Modify: `src-tauri/launcher/index.html`
- Modify: `src-tauri/launcher/launcher.js`
- Modify: `src-tauri/launcher/launcher.css`
- Modify: `src-tauri/launcher/workflow-shell.test.mjs`
- Modify: `src-tauri/launcher/mobile-shell.test.mjs`

- [ ] **Step 1: Write failing shell tests**

Test requirements:

- Settings contains `id="plugins-panel"`.
- Review contains `id="plugin-suggestions-panel"`.
- Launcher fetches `/api/v1/plugins` and `/api/v1/plugins/suggestions` after connection.
- Review renders Approve/Dismiss controls.
- iPhone SE CSS keeps plugin cards single-column and buttons usable.

- [ ] **Step 2: Run tests to verify failure**

Run: `node --test src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs`

Expected: FAIL because UI containers/rendering do not exist.

- [ ] **Step 3: Add HTML containers**

Settings:

```html
<section class="settings-panel plugin-settings-panel" id="plugins-panel">
  <div class="section-heading">
    <p>Plugins</p>
    <h2>Installed extensions</h2>
  </div>
  <div class="plugin-list" id="plugin-list"></div>
</section>
```

Review:

```html
<section class="review-panel plugin-suggestions-panel" id="plugin-suggestions-panel">
  <div class="section-heading">
    <p>Suggestions</p>
    <h2>Plugin review queue</h2>
  </div>
  <div class="plugin-suggestion-list" id="plugin-suggestion-list"></div>
</section>
```

- [ ] **Step 4: Render plugins and suggestions**

In `launcher.js`:

- fetch plugins and suggestions in `connectAndLoad`
- render plugin cards in Settings
- render suggestion cards in Review
- wire Approve/Dismiss buttons to plugin suggestion action endpoints
- refresh dashboard/review after approval when a core object may have been created
- keep empty states concise

- [ ] **Step 5: Add CSS**

Use existing visual language:

- subtle radii
- no gaudy button colors
- compact iPhone layout
- single-column plugin cards below `430px`

- [ ] **Step 6: Run launcher tests**

Run: `node --test src-tauri/launcher/*.test.mjs`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src-tauri/launcher/index.html src-tauri/launcher/launcher.js src-tauri/launcher/launcher.css src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs
git commit -m "Add plugin registry and suggestions UI"
```

---

### Task 8: Full Verification

**Files:** no production edits expected.

- [ ] **Step 1: Format check**

Run: `cargo fmt --all --check`

Expected: PASS.

- [ ] **Step 2: Rust tests**

Run: `cargo test --workspace`

Expected: PASS.

- [ ] **Step 3: Launcher tests**

Run: `node --test src-tauri/launcher/*.test.mjs`

Expected: PASS.

- [ ] **Step 4: Tauri check**

Run: `cargo check --manifest-path src-tauri/Cargo.toml`

Expected: PASS.

- [ ] **Step 5: Diff check**

Run: `git diff --check`

Expected: PASS.

- [ ] **Step 6: Manual smoke**

Run the server and launcher, then verify:

- Settings shows Health and Communications plugins disabled.
- Review shows empty plugin suggestion queue.
- Enabling/disabling a plugin updates Settings.
- A seeded test suggestion, if added through API during development, appears in Review and can be dismissed.

- [ ] **Step 7: Commit verification/doc touch-ups if needed**

```bash
git status --short
git commit -m "Verify plugin platform slice"
```

Only commit if verification required final changes.
