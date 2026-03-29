# Task Mutation Boundary Design

## Goal

Reduce the risk of task edits saving the wrong data by moving task write rules into a single boundary that route handlers call instead of mutating `Task` objects directly.

## Problem

Task writes are currently spread across multiple routes:

- `app/routes/tasks.py`
- `app/routes/homepage.py`
- `app/routes/capture.py`

Those routes each clean form data and perform task state transitions in-place. That creates three failure modes:

1. different write paths normalize the same fields differently,
2. state transitions drift over time,
3. fixing one task-write bug does not automatically protect the other mutation paths.

The most reliability-sensitive areas match the user’s concern:

- task edit/archive/restore actions,
- drag-and-drop or other task moves that change ownership/horizon/inbox state.

## Recommended Approach

Add a small write-focused service module:

- `app/services/task_mutations.py`

This module becomes the single place for:

- parsing and normalizing incoming task update values,
- applying allowed task field changes,
- task lifecycle transitions such as complete, reopen, archive, restore,
- inbox/task movement rules that need consistent state handling.

Routes remain responsible for:

- reading HTTP form/query inputs,
- looking up records,
- formatting redirects/JSON responses.

The new service owns the business rule: what changes are valid and how they are persisted to the task model.

## Scope

### In scope

- centralize task edit normalization now duplicated in `tasks.py` and homepage task creation paths,
- centralize lifecycle transitions used by task archive/restore/complete/reopen actions,
- add regression tests around task update and lifecycle correctness,
- update route handlers to call the service.

### Out of scope

- UI redesign,
- calendar/block editing changes,
- broad capture flow redesign,
- changing existing task concepts or product rules.

## Design Details

### 1. Input normalization

The service should expose a small helper for normalized updates, covering fields such as:

- `verb_noun`
- `description`
- `project_id`
- `when_bucket`
- `block_type`
- `duration_minutes`
- `frog`
- `alignment`

The purpose is not generic abstraction. The purpose is a single trusted implementation for the exact task form fields already used by the app.

### 2. Lifecycle transitions

The service should expose explicit operations like:

- update task fields,
- complete task,
- reopen task,
- archive task,
- restore task,
- archive inbox task.

Each operation should fully own the affected status/inbox/archive/completion fields so routes do not need to remember the correct combinations.

### 3. Route changes

Update these routes first:

- `app/routes/tasks.py`
- `app/routes/homepage.py`

Only pull `app/routes/capture.py` into this pass if the extracted service clearly simplifies an overlapping task transition without expanding the scope too much.

### 4. Tests

Add service-level regression tests that assert:

- task field cleaning is consistent,
- invalid/empty values become the expected normalized model values,
- complete/archive/restore transitions produce the expected task state,
- inbox-origin restores and inbox archive transitions preserve the correct inbox/archive flags.

Existing route tests should continue to pass without behavioral changes.

## Expected Outcome

After this refactor:

- task writes will have a single trusted mutation boundary,
- future task-write bugs will be easier to fix once,
- route handlers will become thinner and less error-prone,
- the planning/task area will be more reliable without changing the user-facing workflow.
