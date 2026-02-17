# Changelog

## 0.732 - 2026-02-17
- Consolidated app version to a single source (`app/version.py`) and wired it into app metadata, header UI version pill, and export manifest metadata.
- Removed deprecated `datetime.utcnow()` usage with shared UTC helpers for timezone-safe timestamps.
- Migrated template rendering to the modern `TemplateResponse(request, template, context)` signature across route handlers.
- Removed inbox container GET-side effects by making recycle cleanup explicit (`POST /inbox/recycle/purge-expired`) instead of mutating during page navigation.
- Added lightweight TTL caching for coach global context to reduce repeated high-volume context queries on rapid page transitions.
- Reduced Cozi request-path blocking risk with shorter configurable HTTP timeout and retry backoff after fetch failures.
- Extracted Training Live inline JS into `app/static/js/health-training-live.js` to improve frontend maintainability.
- Added server-side pagination for task history pages (Completed and Archived) with explicit page controls in the UI.
- Added API pagination envelopes for `/api/projects` and `/api/tasks` with metadata (`items`, `page`, `page_size`, `total`, `total_pages`).
- Expanded accessibility regression checks beyond Home to include key views, dialog semantics, and training live controls.
- Refactored home `landing` route into helper builders for ritual and calendar state assembly to reduce controller complexity.

## 0.731 - 2026-02-16
- Rolled out Phase 1 inbox intent handling for single-user flow: `Process`, `Learning`, `Enjoy`, and `Park` routing from Inbox.
- Added dedicated inbox containers view and kept recycle-bin delete as a distinct action (separate from Park / Let Go).
- Added undo toast behavior for quick inbox routing to reduce accidental item moves.
- Simplified Inbox header actions to reduce clutter (primary actions + `Lists` menu for secondary destinations).
- Improved guided processing flow: clearer support-project dependency, stronger block-type guidance, and reduced modal overflow friction.
- Improved Home UX details: Today calendar auto-scrolls to current time, panel spacing/height tuning, and glow clipping fix.
- Hardened Gmail/dev reliability paths (virtualenv selection for Gmail-enabled web runs, clearer auth/sync handling).
- Updated docs to reflect current inbox intent strategy and waiting behavior.

## 0.721 - 2026-01-28
- Added a Send to Inbox action in the task edit modal for non-inbox tasks.
- Rebuild script now bumps the version pill automatically.

## 0.7.0 - 2026-01-24
- Expanded ritual check-ins with morning focus chunk, midday alignment reset, and evening shutdown/breadcrumbs.
- Added pattern-based Charlie nudges with threshold gating and optional LLM wording.
- Simplified the health dashboard and removed heavy guidance blocks.
- Refined header/nav styling, button sizing, and added inbox count badge.

## 0.6.0 - 2026-01-22
- Added Gmail sync with OAuth auth, background polling, and email-to-inbox import.
- Added inbox detail modal with editable description, linkified preview, and recycle bin actions.
- Split Tasks into separate Active/Completed/Archived pages with dedicated Time/Project views.
- Refined inbox/task UI layout, hover states, and pill styling.

## 0.5.0 - 2026-01-11
- Added export center with time windows, data filters, and ZIP JSON/CSV output.
- Added profile page and onboarding wizard to anchor Why and weekly focus.
- Added tasks board with time/project views, weekly archive flow, and task editing.
- Added weekly review wizard with completion logging and follow-up nudges.
- Improved Charlie with screen-aware guidance and quick actions.
- Refined header navigation sizing and color accents (export + profile).

## 0.4.0 - 2026-01-11
- Added health + fitness dashboard with goals, quick log, and trend board.
- Added diet, weight, fitness, strength, and flexibility tracking pages.
- Added combined blood pressure logging for systolic + diastolic.
- Moved the health check to `/healthz` to make `/health` the dashboard.

## 0.3.0
- Full Weekly review flow.
- Basic summaries of alignment and focus usage.
- Removed the Guide page and header button.
- Added long term planning page at `/long-range` with horizon and roadmap views.
- Added inline project editing and project pyramid view on the long term page.

## 0.2.0
- Added Charlie coach widget with optional local Ollama integration and coach-lite fallback.
- Added in-app Guide page at `/guide` plus coach responses for “how to use” questions.
- Added Cozi ICS integration (`COZI_ICS_URL`) and calendar error surfacing in the UI.
- Added full-width 7-day calendar screen at `/calendar/week`.
- Added lightweight `.env` auto-loader at startup (see `.env.example`).

## 0.1.0 - Prototype

### Added
- FastAPI/Jinja/SQLite scaffold with Start Finishing Organiser branding.
- Core models for projects, tasks, blocks, success packs, waiting on/OPP, rituals, and resurfacing.
- Guided capture wizard (one question at a time: mine/shared/OPP, task vs project, horizon, Why tags, block/energy, duration) with 4+3 weekly cap enforcement and resurface dates for later horizons.
- Capture forms for quick project/task entry with Why prompts and duration.
- Today-first dashboard: Now panel, today schedule, today tasks, today calendar timeline, inbox for parked items.
- Scheduling: assign tasks with duration/block type into blocks; unschedule support; blocks planner view.
- Resurfacing view for Month/Quarter/Later items and weekly review page for 4+3 + resurfacing.
- Ritual flows (morning/midday/evening) with saved entries.
- Waiting On/OPP list tied to capture wizard when owner is OPP.
- Neon theme inspired by Simulation Theory artwork with adjustable pink/blue hover states.
- Utility and migration helpers for enum/value normalisation and new columns (owner_type, duration, resurface_on, ritual table).

### Changed
- Home layout simplified to focus on Today (Inbox, Now, Today schedule, Today tasks, Today calendar).
- Palette tuned to darker neon blue with mixed pink/blue button hovers; page padding widened and top spacing increased.

### Known gaps
- Ritual prompts are basic; no summary/history view.
- Blocks planner is list-based (no drag/drop calendar yet).
- External calendar feeds not wired yet.
- Thrashing detection and Success Pack UI still to be built.
