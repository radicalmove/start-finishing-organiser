# Health Exercise Planner Design

## Goal

Add the first real Health plugin feature to the Rust rewrite: a weekly exercise planner that works well on both Mac and iPhone. The feature should let the user plan gym, cardio, and flexibility sessions across a week, record structured details for each session, and mark sessions as planned, done, or skipped.

This is the first Health slice only. Meal planning and longitudinal health metrics such as weight, blood pressure, waist, and thigh measurements remain follow-on slices.

## User Need

The user wants to plan a week of exercise in SFO rather than keep health planning in a separate app. The plan needs enough structure to be useful:

- Gym work should list individual exercises with sets, reps, and weights when relevant.
- Cardio should capture type, duration, and intensity, for example run, bike, indoor rowing, Zone 2, or VO2 max.
- Flexibility should capture specific stretches or movements, sets, hold length, side if relevant, and notes.
- The phone screen is small, so entry and review must be compact and tap-friendly.

## Scope

In scope:

- Rust core DTOs for health exercise weeks, sessions, and detail rows.
- SQLite tables for exercise sessions and typed session details.
- Repository, service, and API support under `/api/v1/plugins/health/exercise`.
- Backup manifest and SQLite snapshot preservation for new Health exercise tables.
- Launcher UI surfaces in the existing plugin shell, with compact mobile behavior.
- Tests for core serialization, database persistence, service rules, API routes, backup, and launcher view models.

Out of scope for this slice:

- Meal planning.
- Weight, blood pressure, waist, thigh, or other longitudinal metrics.
- Workout analytics, progression graphs, personal records, or automatic recommendations.
- Apple Health integration.
- Reusable programme templates, although the data model should not block templates later.
- Detailed calendar scheduling integration beyond assigning sessions to dates.

## Product Shape

The primary UI should be a weekly Health view. It should show one week at a time, grouped by day. Each day can contain zero or more exercise sessions.

A session has:

- `id`
- `session_date`
- `session_type`: `gym`, `cardio`, or `flexibility`
- `title`
- optional `target_duration_minutes`
- `status`: `planned`, `done`, or `skipped`
- optional `notes`
- typed detail rows appropriate to the session type

Gym detail rows have:

- `exercise_name`
- optional `sets`
- optional `reps`
- optional `weight`
- optional `weight_unit`, defaulting to `kg`
- optional `notes`

Cardio detail rows have:

- `activity_type`
- optional `duration_minutes`
- optional `intensity`
- optional `notes`

Flexibility detail rows have:

- `movement_name`
- optional `sets`
- optional `hold_seconds`
- optional `side`
- optional `notes`

## API Design

Use plugin-scoped routes so Health stays clearly attached to the plugin platform:

- `GET /api/v1/plugins/health/exercise/weeks/{week_start}` returns the week summary, sessions, and typed details.
- `POST /api/v1/plugins/health/exercise/sessions` creates a session with optional detail rows.
- `GET /api/v1/plugins/health/exercise/sessions/{session_id}` returns one session with details.
- `PUT /api/v1/plugins/health/exercise/sessions/{session_id}` replaces the editable session fields and detail rows.
- `POST /api/v1/plugins/health/exercise/sessions/{session_id}/status` updates only `planned`, `done`, or `skipped`.
- `DELETE /api/v1/plugins/health/exercise/sessions/{session_id}` deletes a session and its details.

`week_start` should be a Monday `YYYY-MM-DD`. If a client requests a non-Monday date, the service should normalize it to that date's Monday in the response. This keeps iPhone clients simple and matches the weekly review pattern.

## Service Rules

- The Health plugin must be seeded by the existing plugin platform.
- The exercise planner is first-party, so reading existing exercise data should not require the plugin to be enabled.
- Writing exercise sessions should require the Health plugin to be enabled. This keeps the plugin toggle meaningful without hiding existing data.
- Session title is required after trimming.
- Session date is required.
- Session type controls accepted detail row shape.
- Blank optional text fields normalize to `None`.
- Numeric fields must be positive when present.
- Updating a session replaces its typed detail rows transactionally.
- Deleting a session deletes its typed detail rows.

## Data Model

Use normal SFO-owned Rust tables because Health data is private, durable, and should backup with the main SFO database.

Tables:

- `health_exercise_sessions`
- `health_gym_exercises`
- `health_cardio_exercises`
- `health_flexibility_exercises`

All detail tables should reference `health_exercise_sessions(id)` with cascade delete.

This typed-table approach avoids a generic JSON blob that would be hard to validate and query later. It also keeps future template support straightforward: a later template can reuse the same shape or be copied into these session tables.

## Launcher UX

Settings should continue to show the Health plugin card. The first exercise planner surface should appear as a Health section under the plugin area, initially accessible from Review or Settings. It should not add a new top-level nav item yet.

Mac layout:

- Week header with previous/next week controls.
- Day columns or stacked day cards depending on width.
- Session cards showing type, title, key details, status, and edit/delete controls.
- Add-session form with type-specific detail rows.

iPhone layout:

- A single-column week list grouped by day.
- Add session button near the week heading.
- Session editor as compact stacked controls.
- Detail rows should be full-width with minimal labels and subtle radii.

The first UI can use simple native inputs and compact cards. It should prioritize reliability and easy entry over polished training analytics.

## Error Handling

- API validation errors should return `400` with field-specific messages through the existing `ServiceError::Validation` path.
- Missing sessions should return `404`.
- Disabled Health plugin writes should return `400` with a clear plugin-disabled message.
- UI write failures should show the existing action feedback/error mechanism and leave entered form values intact where practical.

## Testing

Core tests:

- DTO serialization for week/session/detail rows.
- Enum serialization for session type and status.

Database tests:

- Migration creates tables.
- Create/list/get/update/delete exercise sessions.
- Cascade delete removes detail rows.
- Backup manifest and snapshot include health exercise tables.

Service tests:

- Plugin-disabled write guard.
- Week start normalization.
- Blank optional text normalization.
- Positive numeric validation.
- Transactional replacement of typed detail rows.

API tests:

- Week get returns sessions grouped by requested week.
- Create/get/update/status/delete routes work.
- Auth still protects routes through existing middleware.

Launcher tests:

- Client view models render week/day/session summaries.
- Payload builders trim fields and preserve typed details.
- Static shell exposes Health exercise containers without new top navigation.
- Mobile shell keeps Health exercise controls within iPhone SE width.

## Rollout

1. Add core DTOs and database tables.
2. Add repository and service functions with tests.
3. Add API routes and tests.
4. Add backup support and docs.
5. Add launcher view models and UI.
6. Run full verification and publish as a separate PR.

## Follow-On Slices

- Copy last week into a new week.
- Save reusable programme templates.
- Add meal planning.
- Add weight, blood pressure, waist, thigh, and other body metrics.
- Add trend charts and simple review prompts.
- Consider Apple Health import/export only after SFO-owned Health data is stable.
