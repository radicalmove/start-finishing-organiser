# SFO Weekly Review Design

## Goal

Add the first Rust weekly review workflow so the app can move beyond capture, processing, and Today execution into the weekly commitment loop.

This slice should answer three questions:

- What is active this week?
- What parked work is due to come back?
- What completed work can be archived so the week stays clean?

The design should stay narrow. It should not port the full Python weekly wizard, long-range planning board, week calendar, or reflection history in one step.

## Product Reasoning

The Rust rewrite now has enough daily workflow coverage to expose the next product risk. Capture, Process, and Today can create, route, complete, and reopen work. Without a weekly review loop, the system can still accumulate commitments faster than it prunes them.

Weekly review is the right next product slice because it is the control point for the 4+3 rule, resurfacing, and cleanup. It should reduce commitments, not become another admin surface.

The first version should be closer to a focused weekly review board than a wizard. A board is easier to review on Mac, still usable on iPhone, and gives us a clear backend contract before adding richer step-by-step reflection.

## Scope

### In Scope

- Add a `Review` workflow to the shared Tauri shell.
- Add a weekly review summary API that returns:
  - active weekly projects,
  - category counts and caps,
  - due resurface tasks,
  - recently completed tasks for archive cleanup.
- Add a dedicated task action that moves a due resurface task into `week` and clears `resurface_on`.
- Reuse existing project update behavior for weekly focus toggles and cap enforcement.
- Reuse existing task archive behavior for completed-task cleanup.
- Keep review state derived from current project/task data; no new review-log table in this slice.
- Update parity/review docs after implementation.

### Out Of Scope

- Full weekly wizard with persisted reflection notes.
- Week calendar editing and focus block planning.
- Long-range project horizon board.
- Drag-and-drop horizon moves.
- Bulk archive in the first pass.
- New notification/reminder behavior.
- Physical iPhone signing.

## UX Design

### Review Workflow

Add `Review` as a top-level workflow beside Today, Capture, Process, and Settings.

The workflow should have four sections:

- `Weekly Focus`: current active-this-week projects, grouped by work and personal, with visible 4/3 caps.
- `Adjust Focus`: a compact project list with toggles for adding/removing weekly focus.
- `Resurface`: due Month/Quarter/Later tasks with a `Move to Week` action.
- `Clean Up`: completed tasks from the recent week with an `Archive` action.

The page should lead with state, not forms. The user should first see whether the week is overloaded or clean.

### Weekly Focus

The focus section should show:

- Work focus count, e.g. `3 / 4`.
- Personal focus count, e.g. `2 / 3`.
- Active project cards with category, horizon, target date when present, and short success/why text when present.

If a category is at cap, the UI should explain that one project must be dropped or paused before adding another.

### Adjust Focus

The first implementation can use a simple list of active projects with `In week` toggles. The list should avoid becoming a full project editor.

Rules:

- Toggle on uses `PATCH /api/v1/projects/{id}` with `active_this_week: true`.
- Toggle off uses `active_this_week: false`.
- Existing backend weekly-cap errors remain authoritative.
- After a successful toggle, reload the weekly summary and bootstrap summary.

If the full project list is large, cap the initial display and provide simple status copy rather than adding search/filter in this slice.

### Resurface

The resurface section should show pending, non-inbox, non-archived tasks whose `resurface_on` is today or earlier.

Each item should show:

- task title,
- original bucket,
- resurface date,
- linked project title if available later; for this first pass, project ID/title can be omitted unless the summary query can provide it cheaply.

Action:

- `Move to Week` sets `when_bucket = week` and clears `resurface_on`.

This deserves a dedicated service/API method rather than a generic task patch because the two-field transition is a domain rule.

### Clean Up

The cleanup section should show tasks completed during the current weekly review window, excluding archived tasks.

Action:

- `Archive` uses the existing task archive endpoint.

Do not add bulk archive yet. Individual archiving keeps the first pass easy to verify and reduces the chance of accidental cleanup.

### Finish State

The first pass can end with a lightweight local success state:

- `Review updated`
- counts of focus projects, resurfaced tasks remaining, and completed tasks remaining

Do not persist reflection notes yet. Persisted review notes require a real review-log schema and should be a later slice once the board workflow proves useful.

## API Design

### Domain Types

Add weekly review DTOs in `sfo-core`, for example:

- `WeeklyReviewSummary`
- `WeeklyFocusCounts`
- `WeeklyReviewTask`

The summary should be stable enough for Mac and iPhone clients:

```json
{
  "review_date": "2026-05-10",
  "week_starts_on": "2026-05-04",
  "focus_counts": {
    "work": { "current": 3, "cap": 4 },
    "personal": { "current": 2, "cap": 3 }
  },
  "weekly_projects": [],
  "available_projects": [],
  "resurface_due": [],
  "completed_tasks": []
}
```

Use existing `Project` where possible for weekly and available projects. Use a compact task DTO for review task rows if returning full `Task` creates unnecessary client coupling.

### Routes

Add routes under `/api/v1/weekly-review`:

- `GET /api/v1/weekly-review?date=YYYY-MM-DD`
- `POST /api/v1/weekly-review/tasks/{task_id}/move-to-week`

Do not add a dedicated focus-toggle route in the first pass unless existing project patch behavior proves awkward. Keeping project focus as project state is consistent with the existing API.

### Service Rules

Add a `WeeklyReviewService` in `sfo-services`.

Rules:

- Week starts Monday for summary windows.
- Focus counts should use the same category/count rule as weekly cap enforcement, so the visible counts and backend cap errors cannot disagree.
- Available focus candidates include active, non-archived projects. Completed projects should not be offered as candidates.
- Resurface due includes tasks where:
  - `resurface_on <= review_date`,
  - status is neither `done` nor `archived`,
  - `in_inbox = false`.
- Move to week:
  - sets `when_bucket = week`,
  - clears `resurface_on`,
  - leaves project, block type, owner, and first action untouched,
  - leaves status pending/in-progress as-is unless the task is archived/done, in which case return a validation error.
- Completed cleanup candidates include tasks with `status = done`, `completed_at >= week_starts_on`, and not archived.

## Persistence Design

No new table is required for the first slice.

Repository additions in `sfo-db` should be query-focused:

- active weekly project counts by category,
- available focus projects,
- due resurface tasks,
- completed tasks in a date window,
- update task for move-to-week.

The existing project and task tables already have the required fields: `active_this_week`, `status`, `when_bucket`, `resurface_on`, and `completed_at`.

## Client Architecture

Keep the current static Tauri shell architecture:

- `index.html`: add the Review workflow panel.
- `launcher.css`: add responsive review layout using existing SFO aesthetic tokens.
- `client.js`: add weekly review request helpers and pure view-model mapping.
- `launcher.js`: render review sections and wire actions.

The Review workflow should not turn `launcher.js` into a large weekly-review controller. If the implementation gets dense, extract small pure helpers into `client.js` first and only split files if the boundaries are obvious.

## Data Flow

On app load after successful connection:

1. Load bootstrap, inbox containers, project options, and weekly review summary.
2. Render Today, Process, and Review from the shared loaded state.

On Review refresh:

1. Load `GET /api/v1/weekly-review`.
2. Render counts, weekly projects, focus candidates, due resurface tasks, and completed tasks.

On focus toggle:

1. Patch the project with the new `active_this_week` value.
2. Reload weekly review summary and bootstrap.
3. Show action feedback; if cap enforcement fails, show the backend error near the focus section.

On move-to-week:

1. Call the dedicated move-to-week endpoint.
2. Reload weekly review summary and bootstrap.
3. Show reversible-looking copy only if there is a real undo path. For this slice, use plain success feedback.

On archive completed task:

1. Call the existing archive endpoint.
2. Reload weekly review summary and bootstrap.
3. Offer `Restore` only if the existing task restore endpoint is wired into the feedback action.

## Error Handling

- Weekly cap errors should be shown in the Review workflow, not only in a global status area.
- Move-to-week should return a validation error for done or archived tasks.
- If weekly summary loading fails but the app remains connected, keep the rest of the shell usable and show an empty/error state in Review.
- If a Review action succeeds but refresh fails, show that the action was accepted and that refresh needs retry.
- Avoid hiding all review data on one failed action.

## Testing

Add tests before implementation.

Rust tests:

- `sfo-core`: weekly review DTO serialization.
- `sfo-db`: weekly summary queries for focus counts, due resurface tasks, and completed-week tasks.
- `sfo-services`: move-to-week clears `resurface_on` and preserves other task fields.
- `sfo-services`: move-to-week rejects done/archived tasks.
- `sfo-server`: weekly review summary endpoint returns expected JSON.
- `sfo-server`: move-to-week endpoint updates the task and clears resurface date.

Launcher tests:

- Review workflow exists in top-level navigation.
- Review view model exposes focus counts, resurface due items, and cleanup items.
- Focus toggle wiring calls project patch and refreshes review state.
- Move-to-week wiring calls the weekly review endpoint.
- Mobile layout keeps review sections readable without horizontal overflow.

Manual review:

- Seed a disposable database with weekly projects, due resurfacing tasks, and completed tasks.
- Verify the macOS Tauri shell can toggle focus, move due tasks to week, and archive completed tasks.
- Verify the iPhone simulator layout remains usable, especially with five workflow tabs.

## Acceptance Criteria

- `GET /api/v1/weekly-review` returns focus counts, weekly projects, focus candidates, due resurface tasks, and completed tasks.
- `POST /api/v1/weekly-review/tasks/{task_id}/move-to-week` moves a valid due task to Week and clears `resurface_on`.
- Weekly focus toggles are available in the Review workflow and continue to respect the 4+3 cap.
- Due resurface tasks can be moved into Week from the shell.
- Completed recent tasks can be archived from the shell.
- Review is usable on macOS and iPhone simulator without horizontal layout problems.
- Existing Today, Capture, Process, Settings, auth, import, and backup tests remain green.

## Later Slices

- Persist weekly review notes and review completion history.
- Add a true step-by-step weekly wizard.
- Add bulk archive with explicit confirmation.
- Add focus block planning and week calendar editing.
- Add long-range horizon board and drag-and-drop resurfacing.
- Add physical iPhone signing and LAN/VPN review once the user wants hardware validation.
