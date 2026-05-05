# SFO Rust Rewrite Parity And UX Review

Date: 2026-05-06

This review compares the current Python SFO app with the Rust rewrite branch so the rewrite keeps moving by product slices, not route-by-route cloning.

## Current Rust Coverage

The Rust branch currently has:

- Workspace foundation: `sfo-core`, `sfo-db`, `sfo-services`, and `sfo-server`.
- SQLite migrations, WAL-mode connection setup, health checks, and Axum routing.
- Projects API with weekly 4+3 cap enforcement.
- Tasks API with CRUD, pagination, complete, reopen, archive, restore, and quick capture.
- Blocks API with CRUD and task schedule-date sync when task blocks are created or deleted.
- Python SQLite dry-run import and real import for projects/tasks/blocks.
- Rust database backup file creation before import writes.
- Backup manifest endpoint for current Rust tables.

This is a good foundation, but it is still only the planning/task substrate. It does not yet cover the main daily workflow UX.

## Product Parity Matrix

| Product area | Current Python behavior | Rust coverage | UX importance | Recommendation |
| --- | --- | --- | --- | --- |
| Projects | Weekly focus, long-range planning, success cues, roadmaps | Core CRUD and weekly cap | High | Keep extending through long-range/project success fields after daily workflow primitives exist. |
| Tasks | Time/project board, lifecycle, inbox flags, completion/archive history | Core CRUD and lifecycle | High | Covered enough for the next client/bootstrap slice. |
| Quick capture | Modal and capture page can send undecided items to Inbox | API quick capture | High | Keep. It is the right first capture primitive. |
| Guided capture | Wizard decides task/project/inbox/OPP and routes source inbox items | Not covered | Very high | Port after Bootstrap because it defines the app's behavior quality. |
| Inbox containers | Learning, Enjoy, Parked, Recycle bin, undo, metrics | Data fields only | Very high | Port as a dedicated slice, not as incidental task updates. |
| Blocks/calendar | Focus/Admin/Social/Recovery blocks, appointments, week calendar | Core API, import, backup | Very high | Covered enough for a Bootstrap/Home summary slice; UI and external calendars are still pending. |
| Home/Today | Inbox, Today calendar, Now strip, One Thing/Frog, Today tasks | Not covered | Very high | Best next product slice via a Bootstrap/Home summary endpoint. |
| Weekly review | 4+3 focus, resurfacing, block planning, archive completed | Not covered | High | Port after Home primitives; depends on projects, tasks, blocks, resurface. |
| Resurface | Pull Month/Quarter/Later due items into Week | Partly possible through task fields | Medium-high | Add with weekly review or just before it. |
| Waiting On / OPP | Captures other-owned priorities and follow-up dates | Not covered | Medium-high | Port alongside guided capture because OPP creation happens there. |
| Rituals | Morning/midday/evening check-ins and Home status | Not covered | Medium | Defer until Home/Blocks exist. |
| Health | Full health/training module | Not covered | Medium | Large independent slice; do not block first Mac/iPhone planning app. |
| Coach/guidance | Chat, nudges, reminders, pattern detection | Not covered | Medium | Defer until core workflows are stable. |
| Export | ZIP with JSON/CSV, checksums, SQLite snapshot | Backup manifest only | High for safety | Expand after more Rust tables exist. |
| Auth/deployment | Optional auth in Python wrapper | Not covered in Rust | High for Mac mini/iPhone | Add before any real multi-device use. |

## UX Review Targets

When we do the hands-on UX review, focus on workflows rather than screens:

1. Capture to decision: can an unclear thought become the right container without friction?
2. Today execution: does Home make the current block, One Thing, Frog, and Today tasks obvious?
3. Weekly review: does it reduce commitments, or does it become another admin chore?
4. Long-range planning: do horizon views help decide what to finish, or mostly rearrange cards?
5. Health/training: is this a useful tracker, or competing with the planning app's core attention?

The iPhone client should be reviewed against these same workflows. It should not be a compressed desktop UI. The phone version should prioritize capture, Today, inbox processing, quick schedule review, and lightweight weekly check-in.

## Recommended Next Slices

### 1. Bootstrap/Home Summary API

Add a read-only endpoint that gives clients the minimum state needed to draw an initial dashboard: active projects, inbox count, today tasks, today blocks, current/next block, and backup/import status.

Why this should be next:

- Blocks now exist in Rust, so Today can reflect both scheduled time and task intent.
- Mac and iPhone clients need one initial payload before UI work can stay coherent.
- It creates a natural product checkpoint for the later functionality/UX review.

Minimum scope:

- `GET /api/v1/bootstrap`
- Active weekly projects.
- Inbox and container counts.
- Today tasks.
- Today blocks.
- Current/next block based on server time.
- Backup/import capability/status summary.

Out of scope:

- Full HTML Home replacement.
- External Cozi calendar events.
- Personalized recommendations or nudges.

### 2. Inbox Processing And Containers

Port the approved inbox strategy as service behavior:

- Process-time intent classification.
- Learning / Enjoy / Park routing.
- Recycle bin and undo.
- Container counts and metrics.

This is the highest UX-quality slice after the dashboard contract because capture quality is what keeps the app trustworthy.

### 3. Auth And Mac Mini Deployment

Before real phone use, the Rust server needs private-network auth and deployment basics:

- User/session token model.
- Server config file or env contract.
- Launch service/runbook for the Mac mini.
- Backup location policy.

## Completed Slice: Blocks And Calendar Primitives

This slice added Rust domain types, migrations, repository/service functions, API endpoints, backup support, and Python import for blocks.

Why this was the right next slice:

- Blocks are central to the Start Finishing behavior model: attention is reserved in time, not just listed.
- Home, Today calendar, Week calendar, Ritual planning, and Weekly Review all depend on blocks.
- The Python block schema is straightforward and imports after projects/tasks because block rows can reference both.
- It gives future Mac and iPhone clients a concrete scheduling primitive.

Minimum scope:

- `GET /api/v1/blocks`
- `POST /api/v1/blocks`
- `PATCH /api/v1/blocks/{block_id}`
- `DELETE /api/v1/blocks/{block_id}`
- Preserve Python `blocks.id` as `blocks.legacy_id`.
- Map imported `project_id` and `task_id` through existing legacy IDs.

Out of scope for the first Blocks slice:

- External Cozi calendar integration.
- Drag-and-drop calendar UI.
- Complex recurrence.
- Weekly wizard scheduling behavior.

## Current Recommendation

The next coding slice should be **Bootstrap/Home Summary API**. Blocks now provide the scheduling primitive, so the next step is a single dashboard contract that lets Mac and iPhone clients render the first useful daily view without needing to understand every individual backend route.
