# Task Mutation Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize task write rules so edits, archive/restore actions, and inbox/task moves all use one trusted mutation boundary instead of route-specific field mutation logic.

**Architecture:** Add a small `app/services/task_mutations.py` module that owns task field normalization and lifecycle transitions, then update the HTML task and inbox routes to call it. Keep route handlers responsible for HTTP concerns only, and pin the behavior with service-level and route-level regression tests.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, pytest

---

### Task 1: Lock down the desired mutation behavior with tests

**Files:**
- Create: `tests/test_task_mutations.py`
- Modify: `tests/test_inbox_workflows.py`
- Modify: `tests/test_tasks_pages.py`

- [ ] **Step 1: Write failing service tests for task field normalization**

Add `tests/test_task_mutations.py` covering:
- trimmed `verb_noun` and `description`,
- `project_id` handling for `""`, `"null"`, and valid numeric strings,
- `block_type`, `duration_minutes`, `frog`, and `alignment` normalization,
- `send_to_inbox`/reset-to-unprocessed behavior for edits.

- [ ] **Step 2: Run the new service tests to verify they fail**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_task_mutations.py`
Expected: FAIL because `app/services/task_mutations.py` does not exist yet.

- [ ] **Step 3: Add failing lifecycle regression tests**

Extend tests to cover:
- complete task sets `DONE`, clears inbox, and stamps `completed_at`,
- reopen task clears `completed_at` and returns to `PENDING`,
- archive task clears inbox and `archived_from_inbox`,
- restore task respects `archived_from_inbox`,
- inbox archive sets recycle-bin state consistently,
- inbox undo restores unprocessed inbox state.

- [ ] **Step 4: Run inbox/task regression tests to verify at least one fails for the missing shared boundary**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_task_mutations.py tests/test_inbox_workflows.py tests/test_tasks_pages.py`
Expected: FAIL with missing service import or failing new assertions.

### Task 2: Implement the task mutation service

**Files:**
- Create: `app/services/task_mutations.py`
- Modify: `app/services/__init__.py`
- Test: `tests/test_task_mutations.py`

- [ ] **Step 1: Add a focused task mutation module**

Implement explicit operations for:
- task update normalization,
- complete,
- reopen,
- archive,
- restore,
- archive inbox item.

Keep the surface small and concrete; do not build a generic model abstraction.

- [ ] **Step 2: Reuse existing helpers instead of re-encoding business rules**

Call existing helpers such as inbox reset/container helpers where appropriate so state logic stays aligned with the current app rules.

- [ ] **Step 3: Run service tests**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_task_mutations.py`
Expected: PASS

### Task 3: Move route handlers onto the shared boundary

**Files:**
- Modify: `app/routes/tasks.py`
- Modify: `app/routes/homepage.py`
- Modify: `tests/test_inbox_workflows.py`
- Modify: `tests/test_tasks_pages.py`

- [ ] **Step 1: Update `app/routes/tasks.py`**

Replace direct task mutation logic in:
- `/tasks/update`
- `/tasks/complete`
- `/tasks/reopen`
- `/tasks/archive`
- `/tasks/archive/bulk`
- `/tasks/restore`

with calls into `app/services/task_mutations.py`.

- [ ] **Step 2: Update `app/routes/homepage.py` task/inbox writes**

Replace direct task mutation logic in:
- `/tasks/form`
- `/inbox/update`
- `/inbox/archive`
- `/inbox/undo`

with the shared mutation helpers where they fit cleanly.

Leave unrelated homepage behavior untouched.

- [ ] **Step 3: Add route-level regression tests for the shared write path**

Add assertions proving route behavior still matches expectations after the refactor:
- JSON inbox update trims description,
- inbox archive lands in recycle-bin state,
- task restore preserves inbox-origin behavior,
- task update JSON response still reports normalized state correctly.

- [ ] **Step 4: Run focused route tests**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_task_mutations.py tests/test_inbox_workflows.py tests/test_tasks_pages.py`
Expected: PASS

### Task 4: Verify no regressions in adjacent planning/task flows

**Files:**
- Modify: `docs/superpowers/plans/2026-03-29-task-mutation-boundary.md`

- [ ] **Step 1: Run adjacent task/capture coverage**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_api_tasks.py tests/test_capture_quick.py tests/test_capture_wizard.py tests/test_inbox_workflows.py tests/test_tasks_pages.py`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 3: Review diff scope**

Run: `git diff --stat`
Expected: only the new task mutation service, route integration changes, tests, and this plan/spec documentation.

### Task 5: Execute in an isolated workspace

**Files:**
- Modify: `.gitignore` only if needed for worktree hygiene (should already be handled)

- [ ] **Step 1: Create a fresh worktree before implementation**

Run the `superpowers:using-git-worktrees` workflow before any code changes because `main` already has unrelated local edits and this work will touch `app/routes/homepage.py`.

- [ ] **Step 2: Implement this plan in that worktree, not in the current checkout**

Expected: the task-mutation refactor stays isolated from the unrelated in-progress route/UI changes currently sitting in `main`.
