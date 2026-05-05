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
- Bootstrap/Home Summary API with weekly projects, inbox counts, today tasks, today blocks, current/next block, and compact system state.
- Inbox container API with quick routing to Learning/Enjoy/Park, undo, recycle, restore, and container item lists.
- Guided capture API with task/project creation, source inbox intent handling, support-project task conversion, and source-to-project archiving.
- Python SQLite dry-run import and real import for projects/tasks/blocks.
- Rust database backup file creation before import writes.
- Backup manifest endpoint for current Rust tables.

This is a good foundation, but it is still backend-only. It covers the first reversible inbox-routing workflow and the first guided processing API, but not Waiting On/OPP or the native client UX.

## Product Parity Matrix

| Product area | Current Python behavior | Rust coverage | UX importance | Recommendation |
| --- | --- | --- | --- | --- |
| Projects | Weekly focus, long-range planning, success cues, roadmaps | Core CRUD and weekly cap | High | Keep extending through long-range/project success fields after daily workflow primitives exist. |
| Tasks | Time/project board, lifecycle, inbox flags, completion/archive history | Core CRUD and lifecycle | High | Covered enough for the next client/bootstrap slice. |
| Quick capture | Modal and capture page can send undecided items to Inbox | API quick capture | High | Keep. It is the right first capture primitive. |
| Guided capture | Wizard decides task/project/inbox/OPP and routes source inbox items | Backend task/project/source processing API, without OPP | Very high | Add Waiting On / OPP next, then review native client UX. |
| Inbox containers | Learning, Enjoy, Parked, Recycle bin, undo, metrics | Backend route/recycle/restore/containers API | Very high | Add UI/client review after guided processing exists. |
| Blocks/calendar | Focus/Admin/Social/Recovery blocks, appointments, week calendar | Core API, import, backup | Very high | Covered enough for a Bootstrap/Home summary slice; UI and external calendars are still pending. |
| Home/Today | Inbox, Today calendar, Now strip, One Thing/Frog, Today tasks | Read-only Bootstrap summary | Very high | Next UX review checkpoint; One Thing/Frog and rituals still need Rust data support. |
| Weekly review | 4+3 focus, resurfacing, block planning, archive completed | Not covered | High | Port after Home primitives; depends on projects, tasks, blocks, resurface. |
| Resurface | Pull Month/Quarter/Later due items into Week | Partly possible through task fields | Medium-high | Add with weekly review or just before it. |
| Waiting On / OPP | Captures other-owned priorities and follow-up dates | Not covered | Medium-high | Port next so guided capture can represent owner boundaries. |
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

### 1. Waiting On / OPP Backend

Add the missing ownership-boundary slice that guided capture currently defers:

- Rust `waiting_on` table and domain types.
- Create/list/update/resolve Waiting On items.
- Optional `owner_type` support for tasks if still needed in Rust.
- Guided capture integration for OPP captures with `waiting_person`.
- Bootstrap count or summary for future Home clients.

This should come before UI review because the capture UX cannot be judged properly if "someone else owns this" has nowhere to go.

### 2. Auth And Mac Mini Deployment

Before real phone use, the Rust server needs private-network auth and deployment basics:

- User/session token model.
- Server config file or env contract.
- Launch service/runbook for the Mac mini.
- Backup location policy.

## Completed Slice: Bootstrap/Home Summary API

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

## Completed Slice: Inbox Processing And Containers

This slice added the Rust backend for the approved reversible inbox-routing model.

Minimum scope delivered:

- `GET /api/v1/inbox/containers`
- `POST /api/v1/inbox/{task_id}/route`
- `POST /api/v1/inbox/{task_id}/undo`
- `POST /api/v1/inbox/{task_id}/recycle`
- `POST /api/v1/inbox/{task_id}/restore`
- Learning, Enjoy, Parked, and Recycle bin counts and item lists.
- Python-parity mutation semantics for route, undo, recycle, and restore.

Out of scope:

- Full guided `Process` flow.
- Support-project conversion.
- Waiting On / OPP creation.
- Native Mac or iPhone UI.

## Completed Slice: Guided Capture And Support-Project Processing

This slice added the first Rust backend for the primary guided `Process` path.

Minimum scope delivered:

- `POST /api/v1/capture/guided`
- Create guided tasks and projects.
- Enforce displacement acknowledgement for task/project commitments.
- Require project target dates and action-like project titles unless acknowledged.
- Preserve `year` project horizon while mapping `year` tasks to `later`.
- Require explicit inbox intent when processing a source inbox item.
- Route source items to Learning / Enjoy / Park without creating duplicate tasks.
- Convert source inbox items into support-project tasks only when `project_id` is supplied.
- Mark source inbox items as support-project processed and archived when converted into a new project.

Out of scope:

- Waiting On / OPP schema and capture integration.
- Full native Mac/iPhone guided-capture UI.
- Suggestion/heuristic endpoint for task vs project.

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

The next coding slice should be **Waiting On / OPP Backend**. Guided capture can now create tasks/projects and process inbox source items, but it still cannot represent "this is owned by someone else" or follow-up dates.
