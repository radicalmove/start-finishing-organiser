# SFO Test Plan (v0.732)

## Goal
Validate core flows with junk data before real use and manual Trello migration. Add automated
regression coverage for API + capture logic without touching the real database.

## Setup
- Backup current data: copy `sfo.db` to a safe location.
- Seed junk data (this deletes existing rows in `sfo.db`):
  - `python3 scripts/seed_test_data.py --reset`
- Start the app:
  - `uvicorn main:app --reload`

## Automated test suite
### Install dev deps
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt -r requirements-dev.txt`

### Run tests
- `pytest`

### Notes
- Tests use a temporary SQLite database via `SFO_DATABASE_URL` and do not touch `sfo.db`.
- HTML POST routes are exercised using `SFO_API_TOKEN` to bypass CSRF during automated tests.
- Failures should be triaged before manual UI testing.

### Automated coverage
- API auth guard for `/api/*` (401 without token, success with token).
- `/api/projects` CRUD + weekly cap enforcement.
- `/api/tasks` CRUD.
- Guided capture wizard:
  - Displacement check required.
  - Creates task and project flows.
  - Source-item intent routing (support project vs containers).
- Quick capture:
  - Missing title error.
  - Not sure redirects to wizard.
  - Inbox capture creates task.
- Inbox workflow:
  - Quick route to Learning/Enjoy/Park with undo behavior.
  - Recycle-bin action stays distinct from Park.

## Seeded data coverage
- Profile with Why, values, energy, workday.
- 6 work projects + 4 personal projects, mixed weekly focus.
- 30 tasks across buckets and statuses (pending, in progress, done, archived).
- Blocks for focus/admin/recovery.
- Waiting On items with follow-up dates.
- Ritual entries (morning, midday, evening).
- Health metrics with 14 days of entries and 2 goals.
- Coach messages and a weekly review event.

## Core test passes
### Navigation + header
- Buttons present: Charlie, Long Term, Health, Tasks, Export.
- Export button color and Me button alignment look right.
- Header spacing looks tight but readable.

### Home
- Now panel, Today tasks, and calendar render without errors.
- Profile nudge shows if profile is missing (should not show with seed).

### Capture (quick + wizard)
- Add task and project, verify they appear on Home and Tasks.
- Verify weekly cap warnings appear when exceeding 4+3.
- Guided wizard blocks Next/Save until the name field is filled.

### Tasks board
- Toggle between time and project views.
- Edit a task, update when bucket + block type.
- Send a non-inbox task to Inbox from the edit modal; confirm it appears on Home.
- Complete a task, see it in completed list.
- Archive completed tasks in bulk.

### Weekly review + wizard
- Toggle weekly focus (respect 4+3 cap).
- Resurface a task due this week.
- Finish weekly review and confirm success message.

### Waiting On
- Add follow-up dates and confirm list updates.

### Health module
- Dashboard shows latest metrics and goals.
- Combined blood pressure entry works.
- Diet/weight/fitness/strength/flexibility pages show charts and recent entries.

### Export
- Export with each time window and default data sets.
- Confirm ZIP includes JSON + CSV and a summary.json.
- Verify excluded data stays excluded until checked.

### Coach (Charlie)
- Use "Help me with what I'm looking at" on Home, Tasks, Health, Export.
- Confirm guidance is screen-aware and concise.

## Cleanup
- Stop the app.
- Delete `sfo.db` to start fresh for real use.

## MacOS app next step
- Pick a wrapper: Tauri (lighter) vs Electron (faster to prototype).
- Decide distribution method (local dev build vs signed app).
