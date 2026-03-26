# Health View Helper Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract reusable health view helpers out of `app/routes/health.py` and fix health metric seeding so engine reinitialization works in isolated tests and worktrees.

**Architecture:** Introduce a narrow `app/utils/health_views.py` module for pure or mostly-pure health screen helpers, keep route handlers focused on HTTP/database orchestration, and make `ensure_health_metrics()` resolve the active sessionmaker at runtime. This keeps behavior stable while reducing route sprawl and eliminating a test-environment bug.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, SQLite

---

### Task 1: Lock in helper behavior with tests

**Files:**
- Create: `tests/test_health_view_helpers.py`
- Modify: `tests/test_migrations.py`
- Test: `tests/test_health_view_helpers.py`

- [ ] **Step 1: Write failing helper tests**

Add tests for:
- date/float/int/time parsing and normalization,
- safe health return paths,
- slug generation,
- metric stats over recent entries,
- latest-entry extraction,
- JSON payload escaping,
- tracker navigation metadata shape.

- [ ] **Step 2: Run helper tests to verify they fail**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_health_view_helpers.py`
Expected: FAIL because `app.utils.health_views` does not exist yet.

- [ ] **Step 3: Write failing health metric seeding regression**

Add a test proving `ensure_health_metrics()` works after `init_engine()` points at a fresh SQLite database.

- [ ] **Step 4: Run the regression test to verify it fails**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_migrations.py`
Expected: FAIL because `ensure_health_metrics()` still uses a stale sessionmaker.

### Task 2: Implement the minimal helper extraction

**Files:**
- Create: `app/utils/health_views.py`
- Modify: `app/routes/health.py`
- Modify: `app/utils/health.py`
- Test: `tests/test_health_view_helpers.py`

- [ ] **Step 1: Add the new helper module**

Implement the extracted parsing, normalization, tracker metadata, stats, and JSON helpers in `app/utils/health_views.py`.

- [ ] **Step 2: Update the health route to consume the helpers**

Replace duplicated local helper definitions in `app/routes/health.py` with imports from `app.utils.health_views`.

- [ ] **Step 3: Fix runtime sessionmaker lookup**

Change `app/utils/health.py` so `ensure_health_metrics()` opens a session from the active db module at call time.

- [ ] **Step 4: Run focused tests**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q tests/test_health_view_helpers.py tests/test_migrations.py tests/test_health_trackers.py tests/test_health_exercise_plan.py tests/test_health_supplements.py tests/test_health_training_live.py`
Expected: PASS

### Task 3: Verify the full application still passes

**Files:**
- Modify: `docs/superpowers/specs/2026-03-26-health-view-helper-extraction-design.md`
- Modify: `docs/superpowers/plans/2026-03-26-health-view-helper-extraction.md`

- [ ] **Step 1: Run the full test suite**

Run: `/Users/rcd58/sfo/venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 2: Review the diff for scope control**

Run: `git diff --stat`
Expected: only health helper extraction, regression coverage, and planning docs.
