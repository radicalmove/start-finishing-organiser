# SFO iPhone Workflow Shape

Date: 2026-05-08

This note defines the first iPhone client around workflows, not desktop screen parity. The Mac mini Rust server remains the source of truth; the phone is a fast capture and daily-review client that uses the same data.

## Product Principle

The iPhone app should answer: "What can I safely do in 10 to 90 seconds?"

It should not try to be the full Mac planning surface. Planning, weekly commitment editing, project shaping, and larger reviews belong on Mac first. The phone should make it easy to capture, orient, make small routing decisions, and check what is current.

## First iPhone Tabs

### Today

Purpose: show the current day without making the phone another planning dashboard.

Minimum content:

- Now card: current block if present, otherwise One Thing/Frog fallback.
- Next block if present.
- Today's tasks, capped to the few most relevant rows.
- Waiting On count if anything is due or overdue.
- One-tap Refresh.

Allowed edits:

- Mark a task complete/reopen once the Rust task API is already ready for this.
- Edit One Thing/Frog only if the form stays small.

Out of scope:

- Full block calendar editing.
- Weekly project selection.
- Bulk task triage.

### Capture

Purpose: get an idea out of the user's head with almost no ceremony.

Minimum content:

- One large text field.
- Save to Inbox.
- Optional voice dictation later through native platform input, not a custom recorder in the first version.
- Last-captured confirmation with Undo only if the backend supports a safe reversal for the exact action.

Default behavior:

- Every phone capture starts as unprocessed Inbox unless the user deliberately chooses a quick route.
- No project or due-date fields on the first capture screen.

### Process

Purpose: clear small inbox items while standing in a queue or between tasks.

Minimum content:

- One inbox item at a time.
- Fast route actions: Learning, Enjoy, Park, Recycle.
- Undo/restore for those reversible actions.
- Guided decision: Task, Project, Waiting On.

Guided flow:

1. Choose the item type.
2. Confirm title and short note.
3. Show only fields needed for that type.
4. Save and move to the next item.

Phone-specific rule:

- Task and Waiting On should prefer existing projects; creating a new project is allowed but should be a deliberate second step.
- New project creation should keep the Mac shell's target-date and category safeguards.

### Settings

Purpose: connect to the Mac mini server safely.

Minimum content:

- Server URL.
- API token.
- Health/auth status.
- Short explanation of LAN/VPN expectations.

Storage:

- The current Mac shell stores the token in local storage as a temporary compromise.
- The iPhone client should use platform-secure storage before real use.

## Data And API Fit

Current Rust APIs are enough for a first phone prototype:

- `GET /api/v1/bootstrap` for Today.
- `PUT /api/v1/daily-focus` for One Thing/Frog.
- `POST /api/v1/inbox/quick-capture` for Capture.
- `GET /api/v1/inbox/containers` for Process.
- `POST /api/v1/inbox/{task_id}/route` for Learning/Enjoy/Park.
- `POST /api/v1/inbox/{task_id}/undo` for route undo.
- `POST /api/v1/inbox/{task_id}/recycle` and `POST /api/v1/inbox/{task_id}/restore` for Recycle.
- `POST /api/v1/capture/guided` for Task/Project/Waiting On.
- Task lifecycle endpoints for complete/reopen if Today includes task completion.

Likely API refinements before a polished phone build:

- Add a smaller mobile bootstrap query or response shape if `GET /api/v1/bootstrap` becomes too broad.
- Add explicit "next inbox item" support if the phone Process screen should avoid loading all containers.
- Add secure session/token exchange only if the single API token becomes painful.
- Add HTTPS/VPN guidance before using the Mac mini server outside a trusted LAN.

## Offline Position

The first iPhone version should not attempt full offline sync.

Allowed offline behavior later:

- Queue quick captures locally and upload when the server is reachable.
- Show the last successful Today snapshot as read-only.

Avoid in the first version:

- Offline edits to projects, tasks, blocks, or inbox routing.
- Conflict resolution UI.
- Multi-device merge semantics.

This keeps the Mac mini SQLite database authoritative and avoids a sync system before the core product shape is proven.

## Native Shape

The iPhone client should feel native even if it shares Rust domain concepts:

- Large single-purpose screens.
- One primary action per screen.
- Bottom tabs or a simple top-level navigation pattern.
- Native secure storage for server credentials.
- Native keyboard, dictation, and text input behavior.
- Short lists with caps and "open on Mac for more" copy where appropriate.

Do not port the Mac dashboard layout directly.

## First Build Sequence

1. Mobile connection shell: server URL, API token, health/auth status.
2. Today read-only screen from `GET /api/v1/bootstrap`.
3. Quick capture screen using `POST /api/v1/inbox/quick-capture`.
4. One-item-at-a-time Process screen with route/recycle/undo.
5. Guided Process screen for Task/Project/Waiting On.
6. Optional Today task complete/reopen.

## Review Questions

Use these when testing the first phone build:

- Can a thought be captured in under 10 seconds?
- Does Today answer "what now?" without becoming a full dashboard?
- Can one inbox item be processed without reading a manual?
- Is it clear which decisions are better done later on Mac?
- Does the phone reduce friction, or does it create more places to manage work?
