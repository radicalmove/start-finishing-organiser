# SFO Plugin Platform Design

## Summary

Add a small, safe plugin platform to the Rust rewrite before implementing large feature areas such as Health or Outlook/Teams communication support. The first slice is not an arbitrary third-party runtime. It is a server-side registry, permission model, suggestion queue, and UI surface that lets SFO host plugin-shaped modules without letting them silently mutate core planning data or send external messages.

The intended follow-on plugins are:

- **Health**: exercise, diet, training, supplements, metrics, and goals. This can reuse intent and legacy tables from the Python app, and it should be editable from both Mac and iPhone through SFO APIs.
- **Digital Communications**: Outlook, Teams, calendar and correspondence assistance. This should learn response style, prepare drafts, and propose follow-up actions, but it must not send messages or rewrite plans without explicit approval.

## Goals

- Create a plugin registry that SFO can query and display in Settings.
- Give each plugin explicit capabilities and enabled/disabled state.
- Provide a central review queue for plugin-created suggestions and drafts.
- Let approved plugin output become normal SFO tasks, Waiting On items, calendar-block proposals, retained drafts, or other explicitly supported core objects through existing service-layer rules.
- Allow plugin data to live either in core SFO tables or plugin-scoped storage depending on sensitivity and volume.
- Keep plugin logic server-side so Mac and iPhone clients use the same data and rules.
- Preserve the single-user private-network deployment model.

## Non-Goals

- No marketplace, remote install system, plugin signing, or arbitrary untrusted code loading.
- No Outlook, Teams, or Health implementation in the first slice.
- No automatic email or Teams sending.
- No plugin access to raw secrets through the HTTP API.
- No replacement of the existing five top-level SFO workflows in the first slice.
- No general AI agent that can freely mutate the database.

## Recommended Architecture

Use a **server-side plugin platform with reviewable suggestions**.

Plugins run on the SFO server/Mac mini side. The Mac and iPhone apps talk to the normal SFO API and render plugin status, permissions, suggestions, and plugin-specific views. This keeps credentials, sync jobs, AI inference, and failure handling in one place.

The first slice should be implemented as normal Rust crates and tables, not as a dynamic runtime. Future plugin workers can be added later as sidecar processes, but the first milestone should establish stable contracts:

- plugin identity and metadata
- capabilities and permission checks
- plugin suggestion lifecycle
- approval/rejection actions
- plugin status and health reporting
- extension points in Today, Review, Settings, and future plugin views

## Data Model

### `plugins`

Stores registered plugin metadata.

Fields:

- `id`: stable plugin id such as `health` or `communications`
- `name`
- `description`
- `version`
- `enabled`
- `trust_level`: `first_party`, `local_private`, or `external_sidecar`
- `status`: `not_configured`, `ready`, `degraded`, or `disabled`
- `status_detail`
- `created_at`
- `updated_at`

### `plugin_capabilities`

Declares what a plugin may do.

Candidate capability ids:

- `read_sfo_context`
- `create_suggestions`
- `create_tasks`
- `create_waiting_items`
- `health_read`
- `health_write`
- `communications_read_metadata`
- `communications_read_content`
- `communications_create_drafts`
- `calendar_read`
- `calendar_suggest_blocks`

Capabilities should be stored as rows rather than hard-coded booleans so the Settings UI can explain permissions clearly.

Fields:

- `id`
- `plugin_id`
- `capability`
- `enabled`
- `created_at`
- `updated_at`

### `plugin_suggestions`

Central approval queue for plugin output.

Fields:

- `id`
- `plugin_id`
- `kind`: `task`, `waiting`, `draft_message`, `health_prompt`, `calendar_block`, or `generic`
- `title`
- `summary`
- `detail`
- `payload_json`: structured data needed to approve the suggestion
- `source_label`: e.g. `Outlook`, `Teams`, `Health`, `Weekly review`
- `source_uri`: optional opaque link or local reference
- `confidence`: optional numeric score
- `priority`: `low`, `normal`, `high`
- `status`: `pending`, `approved`, `dismissed`, `superseded`, or `failed`
- `created_core_kind`: optional result type after approval
- `created_core_id`: optional result id after approval
- `created_at`
- `updated_at`
- `resolved_at`

The approval path must call normal SFO services. For example, approving a task suggestion uses task creation rules, not raw SQL insertion.

### Plugin-Owned Storage

Health data should eventually live in normal SFO-owned Rust tables because it is personal planning data and should backup/import cleanly with the main database.

High-volume or sensitive communication caches should be plugin-owned. The core SFO database should keep only what SFO needs:

- approved follow-up tasks
- Waiting On items
- calendar-block proposals
- draft metadata
- user-approved summaries
- links or opaque source references

Raw email/Teams content should not become core planning data by default.

## API Design

Add `/api/v1/plugins` routes:

- `GET /api/v1/plugins`: list plugin registry entries with capability summaries.
- `GET /api/v1/plugins/{plugin_id}`: plugin detail, status, enabled state, and capabilities.
- `PATCH /api/v1/plugins/{plugin_id}`: enable/disable plugin and update user-visible settings that are safe for HTTP.
- `GET /api/v1/plugins/suggestions`: list pending and recent suggestions.
- `GET /api/v1/plugins/suggestions/{suggestion_id}`: suggestion detail.
- `POST /api/v1/plugins/suggestions/{suggestion_id}/approve`: approve and convert into a supported core SFO object when applicable.
- `POST /api/v1/plugins/suggestions/{suggestion_id}/dismiss`: dismiss without creating core data.

Optional later routes:

- `POST /api/v1/plugins/{plugin_id}/sync`: request a manual sync for plugins that support it.
- `GET /api/v1/plugins/{plugin_id}/views/{view_id}`: plugin-specific read models for first-party plugin screens.

## UI Design

### Settings

Add a Plugins section inside Settings:

- installed plugin cards
- enabled/disabled state
- status indicator
- capability list in plain language
- last sync/status detail
- actions such as Enable, Disable, Configure, Sync Now

Settings should not become a dense admin console. It should answer: what is installed, what can it access, and is it healthy?

### Today and Review

Add a compact plugin suggestions surface:

- Today can show high-priority pending suggestions only.
- Review can show the fuller queue, grouped by plugin and kind.
- Suggestions should be actionable: Approve, Dismiss, Open Detail.

Plugin suggestions should not pollute the Process inbox by default. If a suggestion is approved as a task or waiting item, then it becomes normal SFO data and appears in the appropriate workflow.

### iPhone

The iPhone app should support:

- viewing plugin status
- approving/dismissing suggestions
- viewing and editing plugin data exposed through SFO APIs, especially Health

The iPhone should not run plugin sync jobs or store external-service secrets locally in the first version.

## Service Rules

- Disabled plugins cannot create new suggestions.
- Suggestions cannot become core SFO data without an explicit approval API call.
- Approval must use the same service-layer validation as normal user-created data.
- High-impact actions such as sending a message are out of scope for core approval. The Communications plugin may create a draft, but sending remains a separate explicit action.
- Blank text fields should normalize consistently with existing SFO service behavior.
- Plugin failures should degrade plugin status, not break the main Today/Capture/Process/Review workflows.
- Plugin-created records should keep source metadata where useful, but core workflows must remain usable if the plugin is later disabled.

## Backup and Import

The backup manifest should include the plugin registry, capabilities, and suggestions.

For plugin-owned stores:

- first-party plugin tables in the main SQLite database are backed up with normal SFO backup
- external sidecar stores need a plugin backup hook later

The first slice should document that sidecar backup hooks are not implemented yet.

Legacy Python health tables should remain unsupported until the Health plugin slice. The plugin platform should make that future import path clearer, not import health data immediately.

## Security and Privacy

This is a private single-user app, but the plugin platform still needs hard boundaries:

- Use explicit capability rows rather than implicit trust.
- Do not expose tokens or service credentials through plugin APIs.
- Keep communication content out of core SFO unless the user approves a summary, task, waiting item, or draft.
- Log plugin actions enough to explain what happened, but avoid storing unnecessary raw message content.
- Keep API-token protection for all plugin routes except public health checks that already exist.

## Testing

Core tests:

- Plugin DTO serialization.
- Capability defaults and status values.
- Suggestion lifecycle status transitions.

DB tests:

- Migration creates plugin tables.
- Registry upsert preserves plugin identity.
- Capability enable/disable works.
- Suggestion create/list/detail/update works.
- Backup manifest includes plugin tables.

Service tests:

- Disabled plugin cannot create suggestions.
- Approval creates the expected core object through normal service rules.
- Dismissal does not create core data.
- Invalid suggestion payload fails cleanly and marks or reports failure without corrupting state.

API tests:

- List plugins.
- Enable/disable plugin.
- List pending suggestions.
- Approve task, Waiting On, calendar-block, and retained-draft suggestions.
- Dismiss suggestions.
- Auth still protects plugin routes.

Launcher tests:

- Settings renders plugin cards and capability copy.
- Suggestions render compactly on Review.
- iPhone layout keeps plugin status and suggestion actions usable on iPhone SE width.

Verification commands:

```bash
cargo fmt --all --check
cargo test --workspace
node --test src-tauri/launcher/*.test.mjs
cargo check --manifest-path src-tauri/Cargo.toml
git diff --check
```

## Implementation Sequence

1. Add plugin core types and database migration.
2. Add repository and service support for registry, capabilities, and suggestions.
3. Add API routes and tests.
4. Add backup support.
5. Add Settings plugin registry UI.
6. Add Review suggestion queue UI.
7. Add minimal seed registration for two disabled first-party plugins: `health` and `communications`.
8. Document follow-on slices for Health and Communications.

## Follow-On Plugin Slices

### Health Plugin

Port Rust health data tables and APIs after the plugin platform exists. Health should be first-party, editable from iPhone, and backed up with the main SFO database.

Initial Health scope should be smaller than the full Python module:

- metrics
- entries
- goals
- exercise/training logs
- simple dashboard summary

### Communications Plugin

Build after the suggestion queue and approval model are proven.

Initial Communications scope should be conservative:

- read recent Outlook/Teams metadata and selected message content
- summarize likely follow-ups
- create draft replies
- create suggested SFO tasks or Waiting On items
- never send automatically

Style learning should start from explicit user-approved examples and drafts, not silent mining of all correspondence.

## Open Risks

- The launcher is currently a static JavaScript shell. Plugin-specific screens may push it toward a more modular frontend architecture.
- Sidecar plugin workers will need lifecycle management, logs, and backup hooks later.
- Microsoft integration may require current Graph/Outlook/Teams API constraints and authentication details that are not yet designed.
- Health could become a full app inside SFO. The first Health slice must stay smaller than the old Python module.
