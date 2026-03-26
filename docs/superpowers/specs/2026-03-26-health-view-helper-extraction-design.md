# Health View Helper Extraction Design

## Goal

Reduce the size and responsibility of `app/routes/health.py` without changing the user-facing health workflows, while also fixing the `SessionLocal` binding bug in `app/utils/health.py` that breaks clean engine reinitialization in isolated test environments.

## Current Problem

The health route module mixes several concerns:

- request handling and database orchestration,
- input parsing and normalization,
- tracker navigation metadata,
- payload shaping for inline JSON blobs,
- simple statistics helpers.

That makes the route harder to read and raises the cost of adding or reviewing health changes. Separately, `ensure_health_metrics()` imports `SessionLocal` directly, which leaves it bound to the original sessionmaker even after `init_engine()` swaps the database engine during tests.

## Recommended Approach

Create a focused helper module for health view concerns and keep `app/routes/health.py` as the orchestration layer.

### New helper module

Add `app/utils/health_views.py` to own:

- tracker tab metadata,
- parsing and normalization helpers,
- safe return-path handling,
- JSON payload escaping,
- metric stats and latest-entry helpers.

These are mostly pure or near-pure functions and are a good fit for direct unit coverage.

### Route changes

Update `app/routes/health.py` to import these helpers instead of defining them inline. The route should keep:

- database queries,
- redirects/responses,
- screen-level composition.

### SessionLocal fix

Update `app/utils/health.py` so `ensure_health_metrics()` resolves `SessionLocal` from the db module at runtime instead of holding a stale imported reference. This keeps behavior unchanged in production and makes test/worktree initialization reliable.

## Testing

Add regression tests first for:

- helper parsing/normalization behavior,
- tracker nav metadata exposure,
- metric statistics calculations,
- `ensure_health_metrics()` working after `init_engine()` points at a fresh database.

Then rerun the existing health-focused route tests and the full suite.

## Non-Goals

- No UI redesign.
- No health feature additions.
- No broad route/service refactor outside the health area.
