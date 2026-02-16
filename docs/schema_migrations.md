# Schema Migrations

SFO uses a lightweight migration tracker for single-user SQLite upgrades.

## How it works

- Startup calls `apply_schema_migrations()`.
- Applied revisions are recorded in `schema_migrations`.
- Each revision has a `rollback_hint`.
- Revisions are additive/idempotent where possible.

## Current revisions

- `20260216_001_task_owner_column`: ensure `tasks.owner_type`.
- `20260216_002_task_resurface_columns`: ensure `tasks.resurface_on` and `tasks.duration_minutes`.
- `20260216_003_block_title_column`: ensure `blocks.title`.
- `20260216_004_ritual_table`: ensure `ritual_entries` exists.
- `20260216_005_ritual_columns`: ensure added ritual fields exist.
- `20260216_006_guidance_snoozed_until`: ensure `guidance_reminders.snoozed_until`.
- `20260216_007_task_inbox_column`: ensure `tasks.in_inbox`.
- `20260216_008_task_archived_from_inbox_column`: ensure `tasks.archived_from_inbox`.
- `20260216_009_project_color_column`: ensure `projects.color_scheme`.
- `20260216_010_core_indexes`: ensure core task/calendar/coach indexes.

## Rollback approach

1. Create an export backup ZIP from `/export`.
2. Verify checksums in `backup_manifest.json`.
3. Restore `database.sqlite3` from backup if required.

Do not hand-drop data tables without a verified restore point.
