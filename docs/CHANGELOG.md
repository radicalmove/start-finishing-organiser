# Changelog

## 0.2.0 (planned)
- Placeholder for the next phase of changes.

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
