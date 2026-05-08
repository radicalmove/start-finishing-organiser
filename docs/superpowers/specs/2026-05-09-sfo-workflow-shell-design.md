# SFO Workflow Shell Design

## Goal

Replace the current all-in-one Rust launcher dashboard with a workflow shell that can grow into both the Mac review app and the iPhone app without compressing the old Python dashboard onto a phone screen.

The shell should organize the existing Rust capabilities into four top-level workflows:

- `Today`
- `Capture`
- `Process`
- `Settings`

This slice should not add new database tables or backend routes. The current Rust API is sufficient for the first version.

## Product Reasoning

The Python Home screen is powerful but dense. It combines Inbox, Today calendar, Now, One Thing/Frog, rituals, Today tasks, quick capture, guided capture, shortcuts, and coach affordances in one dashboard. That works as a Mac cockpit, but it is the wrong shape for iPhone.

The Rust backend already supports the core daily workflows: bootstrap summary, daily focus, quick capture, inbox containers, reversible inbox routing, guided conversion, Waiting On, and task lifecycle endpoints. The next product risk is not backend coverage. The risk is letting the first native client become a single overloaded page.

The workflow shell should make the app feel like four short paths:

- "What should I pay attention to now?"
- "Get this thought out of my head."
- "Clear one loose end."
- "Is this device connected safely?"

## Scope

### In Scope

- Add top-level workflow navigation inside the static Tauri launcher.
- Keep the adaptive SFO neon aesthetic baseline.
- Move the existing connection card into `Settings`.
- Move the current bootstrap summary into `Today`.
- Move quick capture into a dedicated `Capture` workflow.
- Move inbox routing and guided conversion into `Process`.
- Keep all workflows backed by the current API calls.
- Keep the implementation static: HTML, CSS, and vanilla JavaScript.

### Out Of Scope

- New database schema.
- New Rust API routes.
- Full Python parity for calendar editing, rituals, coach, weekly review, health, long-range planning, or full task boards.
- Offline sync.
- Physical iPhone signing or Mac mini deployment changes.
- Replacing the static shell with a frontend framework.

## Workflow Design

### Today

Purpose: answer "what now?" without becoming another full dashboard.

Content:

- Connection state in compact form.
- Today label and current time.
- Now card using current block when present.
- Next block when present.
- One Thing and Frog summary.
- Small editable One Thing/Frog form, if it remains visually compact.
- Today task list, capped to the most relevant rows.
- Today blocks as short cards.
- Waiting On count only when useful.
- Ritual status as a compact context item, not a full ritual form.

Allowed actions:

- Refresh.
- Save One Thing/Frog.
- Complete/reopen Today tasks only if the UI can keep this simple.

Avoid:

- Full calendar editing.
- Weekly focus management.
- Project shaping.
- Large connection settings panels.

### Capture

Purpose: capture a thought in under ten seconds.

Content:

- One large text field.
- Primary `Save to Inbox` action.
- Recent success feedback.
- Short explanation that phone capture starts as unprocessed Inbox by default.

Behavior:

- Use `POST /api/v1/inbox/quick-capture`.
- After save, clear the input and keep focus in the field.
- Show a confirmation state.

Avoid:

- Project selectors.
- Dates.
- Horizons.
- Full guided capture.

Those decisions belong in `Process` or on Mac.

### Process

Purpose: process one loose end at a time.

Content:

- One primary inbox item at the top.
- Fast route actions: Learning, Enjoy, Park, Recycle.
- Undo/restore feedback for reversible actions.
- A compact guided decision area for Task, Project, or Waiting On.
- Optional "next item" affordance after a decision.

Behavior:

- Load unprocessed items from `GET /api/v1/inbox/containers`.
- Prefer one-item-at-a-time interaction on phone-sized layouts.
- Allow Mac-width layouts to show a short queue, but the active item should still be obvious.
- Use existing route, undo, recycle, restore, and guided capture endpoints.

Avoid:

- Showing every field at once.
- Treating the guided form like a database editor.
- Creating a new project too casually. Project creation should feel deliberate because it adds commitment.

### Settings

Purpose: make the Mac mini/server relationship explicit and safe.

Content:

- Server URL.
- API token.
- Health/auth status.
- Phone reachability guidance.
- Transport guidance for private HTTP vs HTTPS.
- Storage guidance showing Apple Keychain when the Tauri bridge is available.

Behavior:

- Reuse current connection guidance and Keychain-backed token storage.
- Keep Settings visually quieter than Today/Capture/Process.
- Keep invalid URL and connection errors visible.

## Architecture

Keep the current static launcher architecture:

- `index.html` owns the workflow regions and top-level navigation.
- `launcher.css` owns layout, responsive behavior, and aesthetic tokens.
- `client.js` owns pure view-model and request helpers.
- `launcher.js` owns DOM state, navigation state, rendering, and event wiring.

The implementation should avoid a large rewrite. The first pass can keep one HTML page and one JavaScript entry point, but it should introduce clearer internal boundaries:

- A workflow state value such as `today`, `capture`, `process`, or `settings`.
- Render helpers that are grouped by workflow.
- Existing pure helpers in `client.js` remain testable without DOM.

If `launcher.js` becomes hard to reason about, split only after the workflow shell is green. Do not introduce a frontend framework for this slice.

## Data Flow

On app start:

1. Load server URL and API token.
2. Render Settings guidance from the current values.
3. Connect to `/healthz` and `/api/v1/auth/status`.
4. If auth is satisfied, load:
   - `GET /api/v1/bootstrap`
   - `GET /api/v1/inbox/containers`
   - `GET /api/v1/projects?page=1&page_size=100`
5. Render Today and Process from those responses.

On quick capture:

1. Submit `POST /api/v1/inbox/quick-capture`.
2. Show confirmation.
3. Reload bootstrap and inbox containers.

On Process route/recycle/undo:

1. Submit the relevant inbox endpoint.
2. Show reversible feedback where supported.
3. Reload inbox containers and bootstrap counts.

On guided conversion:

1. Submit `POST /api/v1/capture/guided`.
2. Show non-reversible success feedback.
3. Reload inbox containers, bootstrap, and project options if needed.

## Error Handling

- Keep connection errors in the global status area and Settings workflow.
- Keep workflow action errors close to the action that failed.
- Do not hide existing data just because a refresh fails; if possible, preserve the last rendered state and show the error.
- Distinguish auth-required, invalid URL, server unreachable, and validation errors.
- Keep non-reversible guided conversions explicit in feedback copy.

## Testing

Add or update Node tests for:

- Workflow navigation structure exists in `index.html`.
- The shell exposes exactly the intended top-level workflows.
- Capture view model/copy keeps quick capture simple.
- Process view model can select the primary inbox item and expose a bounded queue.
- Existing connection guidance and secure-token tests remain green.
- Existing aesthetic baseline tests remain green.

Manual review:

- Build/open the Tauri dev shell.
- Verify all four workflows render.
- Verify Today remains readable on desktop.
- Verify a narrow/mobile width does not show a compressed dashboard.
- Verify quick capture still writes through.
- Verify route/recycle/undo still work.
- Verify Settings still reports Keychain storage in Tauri.

## Acceptance Criteria

- The launcher has visible top-level workflows: `Today`, `Capture`, `Process`, and `Settings`.
- The connection form no longer dominates the default connected state.
- Quick capture is available as its own short workflow.
- Process is organized around clearing inbox items, not around a dense all-fields form.
- The implementation uses the current API surface only.
- Existing launcher tests pass.
- The workflow shell still follows the SFO aesthetic baseline.
