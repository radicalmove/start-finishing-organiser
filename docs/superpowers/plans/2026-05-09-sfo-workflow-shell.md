# SFO Workflow Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the all-in-one Rust launcher dashboard with a four-workflow shell: Today, Capture, Process, and Settings.

**Architecture:** Keep the existing static Tauri launcher architecture: `index.html` for regions, `launcher.css` for layout/aesthetic, `client.js` for pure helpers, and `launcher.js` for DOM state and API wiring. Do not add backend routes, schema, a frontend framework, or generated build tooling.

**Tech Stack:** Static HTML/CSS, vanilla JavaScript modules, Node test runner, existing Tauri dev shell.

---

## File Structure

- Modify `src-tauri/launcher/index.html`: add workflow navigation and split the existing dashboard into `Today`, `Capture`, `Process`, and `Settings` sections while preserving existing form/control IDs where practical.
- Modify `src-tauri/launcher/launcher.css`: add workflow-shell layout, responsive navigation, phone-width behavior, and keep the SFO aesthetic baseline.
- Modify `src-tauri/launcher/client.js`: add pure workflow helpers for workflow metadata, capture copy, and primary process-item selection.
- Modify `src-tauri/launcher/client.test.mjs`: add tests for the new pure helpers.
- Create `src-tauri/launcher/workflow-shell.test.mjs`: static tests for workflow regions, navigation, and default shell structure.
- Modify `src-tauri/launcher/launcher.js`: add workflow state/navigation, render the existing data into the new workflow regions, and keep current API calls.
- Existing tests to preserve: `src-tauri/launcher/aesthetic-baseline.test.mjs`, `src-tauri/launcher/mobile-shell.test.mjs`, `src-tauri/launcher/dev-launch.test.mjs`, `src-tauri/launcher/mobile-scaffold.test.mjs`.

## Task 1: Static Workflow Shell Guard

**Files:**
- Create: `src-tauri/launcher/workflow-shell.test.mjs`
- Inspect: `src-tauri/launcher/index.html`

- [ ] **Step 1: Write the failing static structure test**

Create `src-tauri/launcher/workflow-shell.test.mjs`:

```js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const indexHtmlPath = new URL("./index.html", import.meta.url);

test("launcher exposes the four top-level workflows", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  for (const workflow of ["today", "capture", "process", "settings"]) {
    assert.match(indexHtml, new RegExp(`data-workflow-tab="${workflow}"`));
    assert.match(indexHtml, new RegExp(`data-workflow-panel="${workflow}"`));
  }

  assert.match(indexHtml, /<nav class="workflow-nav"/);
  assert.match(indexHtml, /Today/);
  assert.match(indexHtml, /Capture/);
  assert.match(indexHtml, /Process/);
  assert.match(indexHtml, /Settings/);
});

test("connection settings are scoped to the Settings workflow", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const settingsPanelStart = indexHtml.indexOf('data-workflow-panel="settings"');
  const connectionCard = indexHtml.indexOf('id="connection-card"');

  assert.ok(settingsPanelStart >= 0, "settings workflow exists");
  assert.ok(connectionCard > settingsPanelStart, "connection card lives inside settings");
});
```

- [ ] **Step 2: Run the static test to verify it fails**

Run:

```bash
node --test src-tauri/launcher/workflow-shell.test.mjs
```

Expected: FAIL because `index.html` does not yet expose `data-workflow-tab` or `data-workflow-panel`.

- [ ] **Step 3: Do not implement yet**

Commit nothing in this task. The red test is the checkpoint for Task 2.

## Task 2: Add Workflow HTML Structure

**Files:**
- Modify: `src-tauri/launcher/index.html`
- Test: `src-tauri/launcher/workflow-shell.test.mjs`

- [ ] **Step 1: Add the workflow nav**

In `src-tauri/launcher/index.html`, place this after the hero/status area and before workflow panels:

```html
<nav class="workflow-nav" aria-label="Primary workflows">
  <button class="workflow-tab is-active" type="button" data-workflow-tab="today" aria-selected="true">Today</button>
  <button class="workflow-tab" type="button" data-workflow-tab="capture" aria-selected="false">Capture</button>
  <button class="workflow-tab" type="button" data-workflow-tab="process" aria-selected="false">Process</button>
  <button class="workflow-tab" type="button" data-workflow-tab="settings" aria-selected="false">Settings</button>
</nav>
```

- [ ] **Step 2: Split the existing content into workflow panels**

Use these panel wrappers:

```html
<section class="workflow-panel" data-workflow-panel="today" id="workflow-today">...</section>
<section class="workflow-panel hidden" data-workflow-panel="capture" id="workflow-capture">...</section>
<section class="workflow-panel hidden" data-workflow-panel="process" id="workflow-process">...</section>
<section class="workflow-panel hidden" data-workflow-panel="settings" id="workflow-settings">...</section>
```

Move existing content as follows:

- `Settings`: existing `connection-card`.
- `Today`: `dashboard-topline`, `action-feedback`, `daily-focus-form`, Now card, Daily Context card, Today Tasks card, Today Blocks card.
- `Capture`: existing `quick-capture-form`, retitled as a focused capture workflow with explanatory copy.
- `Process`: Inbox count card and inbox processing panel.

Keep existing IDs where possible: `connection-form`, `quick-capture-form`, `daily-focus-form`, `inbox-items`, `today-tasks`, `today-blocks`, `status`, `detail`.

- [ ] **Step 3: Run the static test**

Run:

```bash
node --test src-tauri/launcher/workflow-shell.test.mjs
```

Expected: PASS.

- [ ] **Step 4: Run existing static guards**

Run:

```bash
node --test src-tauri/launcher/aesthetic-baseline.test.mjs src-tauri/launcher/mobile-shell.test.mjs
```

Expected: PASS. If the aesthetic test fails only because copy moved, update the assertion to look for still-valid SFO shell copy, not for removed prose.

- [ ] **Step 5: Commit**

```bash
git add src-tauri/launcher/index.html src-tauri/launcher/workflow-shell.test.mjs
git commit -m "feat: add workflow shell structure"
```

## Task 3: Add Pure Workflow View Helpers

**Files:**
- Modify: `src-tauri/launcher/client.js`
- Modify: `src-tauri/launcher/client.test.mjs`

- [ ] **Step 1: Write failing helper tests**

Add imports in `src-tauri/launcher/client.test.mjs`:

```js
  WORKFLOWS,
  buildCaptureWorkflowViewModel,
  buildProcessWorkflowViewModel,
```

Add tests:

```js
test("workflow metadata exposes the intended app paths", () => {
  assert.deepEqual(
    WORKFLOWS.map((workflow) => workflow.id),
    ["today", "capture", "process", "settings"],
  );
  assert.equal(WORKFLOWS[0].label, "Today");
});

test("capture workflow keeps quick capture focused", () => {
  assert.deepEqual(buildCaptureWorkflowViewModel(), {
    title: "Capture to Inbox",
    description: "Get the thought out of your head. Decide what it means later in Process.",
    placeholder: "Type the thing you are capturing...",
    primaryAction: "Save to Inbox",
  });
});

test("process workflow chooses one primary inbox item and a bounded queue", () => {
  const model = buildProcessWorkflowViewModel({
    counts: { unprocessed: 3 },
    unprocessed: [
      { id: "task-1", verb_noun: "First", description: "", created_at: null },
      { id: "task-2", verb_noun: "Second", description: "", created_at: null },
      { id: "task-3", verb_noun: "Third", description: "", created_at: null },
    ],
  });

  assert.equal(model.activeItem.id, "task-1");
  assert.equal(model.positionLabel, "1 of 3");
  assert.deepEqual(
    model.queue.map((item) => item.id),
    ["task-1", "task-2", "task-3"],
  );
});

test("process workflow handles an empty inbox", () => {
  const model = buildProcessWorkflowViewModel({ counts: {}, unprocessed: [] });

  assert.equal(model.activeItem, null);
  assert.equal(model.positionLabel, "Inbox clear");
  assert.deepEqual(model.queue, []);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
node --test src-tauri/launcher/client.test.mjs
```

Expected: FAIL because the new exports do not exist.

- [ ] **Step 3: Implement the minimal helpers**

Add to `src-tauri/launcher/client.js`:

```js
export const WORKFLOWS = [
  { id: "today", label: "Today" },
  { id: "capture", label: "Capture" },
  { id: "process", label: "Process" },
  { id: "settings", label: "Settings" },
];

export function buildCaptureWorkflowViewModel() {
  return {
    title: "Capture to Inbox",
    description: "Get the thought out of your head. Decide what it means later in Process.",
    placeholder: "Type the thing you are capturing...",
    primaryAction: "Save to Inbox",
  };
}

export function buildProcessWorkflowViewModel(containers, activeIndex = 0) {
  const base = buildInboxProcessingViewModel(containers);
  const safeIndex = Math.max(0, Math.min(Number(activeIndex) || 0, base.items.length - 1));
  const activeItem = base.items[safeIndex] || null;

  return {
    ...base,
    activeItem,
    activeIndex: activeItem ? safeIndex : -1,
    queue: base.items.slice(0, 6),
    positionLabel: activeItem ? `${safeIndex + 1} of ${base.items.length}` : "Inbox clear",
  };
}
```

- [ ] **Step 4: Run the helper tests**

Run:

```bash
node --test src-tauri/launcher/client.test.mjs
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src-tauri/launcher/client.js src-tauri/launcher/client.test.mjs
git commit -m "feat: add workflow view helpers"
```

## Task 4: Wire Workflow Navigation And Rendering

**Files:**
- Modify: `src-tauri/launcher/launcher.js`
- Modify: `src-tauri/launcher/index.html`
- Modify: `src-tauri/launcher/client.js` if Task 3 helpers need small adjustment
- Test: `src-tauri/launcher/client.test.mjs`
- Test: `src-tauri/launcher/workflow-shell.test.mjs`

- [ ] **Step 1: Add DOM references for workflows**

In `src-tauri/launcher/launcher.js`, extend `elements`:

```js
workflowTabs: [...document.querySelectorAll("[data-workflow-tab]")],
workflowPanels: [...document.querySelectorAll("[data-workflow-panel]")],
captureTitle: document.getElementById("capture-title"),
captureDescription: document.getElementById("capture-description"),
processPosition: document.getElementById("process-position"),
```

Add matching IDs in `index.html` where needed.

- [ ] **Step 2: Add workflow state helpers**

Add:

```js
let activeWorkflow = "today";

function setWorkflow(workflow) {
  const nextWorkflow = ["today", "capture", "process", "settings"].includes(workflow)
    ? workflow
    : "today";
  activeWorkflow = nextWorkflow;
  document.body.dataset.workflow = nextWorkflow;

  for (const tab of elements.workflowTabs) {
    const selected = tab.dataset.workflowTab === nextWorkflow;
    tab.classList.toggle("is-active", selected);
    tab.setAttribute("aria-selected", String(selected));
  }

  for (const panel of elements.workflowPanels) {
    panel.classList.toggle("hidden", panel.dataset.workflowPanel !== nextWorkflow);
  }
}
```

- [ ] **Step 3: Wire tab clicks**

Add event listener:

```js
for (const tab of elements.workflowTabs) {
  tab.addEventListener("click", () => {
    setWorkflow(tab.dataset.workflowTab);
  });
}
```

- [ ] **Step 4: Move connection-error fallback to Settings**

In `connectAndLoad` catch block, after `setConnectionState(...)`, call:

```js
setWorkflow("settings");
```

Do not force Settings after a successful connection. The connected default should remain Today.

- [ ] **Step 5: Render Capture copy**

Import `buildCaptureWorkflowViewModel` and apply it during initialization:

```js
function renderCaptureWorkflow() {
  const model = buildCaptureWorkflowViewModel();
  elements.captureTitle.textContent = model.title;
  elements.captureDescription.textContent = model.description;
  elements.quickCaptureInput.placeholder = model.placeholder;
  elements.quickCaptureForm.querySelector('button[type="submit"]').textContent = model.primaryAction;
}
```

- [ ] **Step 6: Render Process from process workflow model**

Import `buildProcessWorkflowViewModel`.

In `connectAndLoad`, replace the existing `renderInboxProcessing(buildInboxProcessingViewModel(...))` call with:

```js
renderProcessWorkflow(
  buildProcessWorkflowViewModel(inboxContainers),
  buildProjectOptions(projectsPage),
  defaultGuidedProjectTargetDate(dashboardModel.todayLabel),
);
```

Rename `renderInboxProcessing` to `renderProcessWorkflow` or keep the existing function name if the implementation stays smaller. The rendered UI must make the first item visually primary and show `process-position`.

- [ ] **Step 7: Run JS checks**

Run:

```bash
node --test src-tauri/launcher/client.test.mjs src-tauri/launcher/workflow-shell.test.mjs
node --check src-tauri/launcher/launcher.js
node --check src-tauri/launcher/client.js
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src-tauri/launcher/index.html src-tauri/launcher/launcher.js src-tauri/launcher/client.js src-tauri/launcher/client.test.mjs
git commit -m "feat: wire workflow shell navigation"
```

## Task 5: Workflow Shell Styling And Mobile Behavior

**Files:**
- Modify: `src-tauri/launcher/launcher.css`
- Modify: `src-tauri/launcher/aesthetic-baseline.test.mjs` only if the static guard needs to recognize renamed classes
- Test: `src-tauri/launcher/aesthetic-baseline.test.mjs`
- Test: `src-tauri/launcher/mobile-shell.test.mjs`

- [ ] **Step 1: Add CSS for navigation and workflow panels**

Add styles for:

```css
.workflow-nav { ... }
.workflow-tab { ... }
.workflow-tab.is-active { ... }
.workflow-panel { ... }
.workflow-lede { ... }
.workflow-grid { ... }
.process-primary { ... }
.process-queue { ... }
.settings-panel { ... }
```

Rules:

- Keep button radius at `var(--sfo-radius-button)`.
- Keep Settings visually quieter than Today/Capture/Process.
- Keep Capture simple: one large field and one primary action.
- On narrow widths, show one workflow panel at a time and avoid side-by-side dashboard grids.

- [ ] **Step 2: Add or update static CSS assertions if useful**

If the CSS introduces new button classes, update `aesthetic-baseline.test.mjs` to ensure they do not use `999px` pill radii.

- [ ] **Step 3: Run CSS/static tests**

Run:

```bash
node --test src-tauri/launcher/aesthetic-baseline.test.mjs src-tauri/launcher/mobile-shell.test.mjs src-tauri/launcher/workflow-shell.test.mjs
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src-tauri/launcher/launcher.css src-tauri/launcher/aesthetic-baseline.test.mjs
git commit -m "style: polish workflow shell layout"
```

## Task 6: Full Launcher Verification

**Files:**
- Verify: `src-tauri/launcher/*.test.mjs`
- Verify: `src-tauri/launcher/launcher.js`
- Verify: `src-tauri/launcher/client.js`
- Inspect: `src-tauri/launcher/index.html`
- Inspect: `src-tauri/launcher/launcher.css`

- [ ] **Step 1: Run all launcher tests**

Run:

```bash
node --test src-tauri/launcher/*.test.mjs
```

Expected: PASS with all launcher tests green.

- [ ] **Step 2: Run syntax checks**

Run:

```bash
node --check src-tauri/launcher/launcher.js
node --check src-tauri/launcher/client.js
```

Expected: no output and exit 0.

- [ ] **Step 3: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output and exit 0.

- [ ] **Step 4: Build/open the Tauri dev shell**

Run:

```bash
scripts/run_tauri_dev_shell.sh
```

Expected:

- `Start Finishing Organiser Dev.app` builds and opens.
- The shell connects to the local Rust server if one is running.
- Today, Capture, Process, and Settings tabs are visible.

- [ ] **Step 5: Manual functional smoke review**

With a local Rust server running:

- Today renders current status without the Settings card dominating the first view.
- Settings still shows server URL, API token, reachability, transport, auth, and storage guidance.
- Capture saves a new item to Inbox.
- Process shows that captured item.
- Learning/Enjoy/Park route actions work and show Undo.
- Recycle works and shows Restore.
- Guided conversion still submits for Task, Project, and Waiting On using the existing API.

- [ ] **Step 6: Commit any final fixes**

If verification required fixes:

```bash
git add src-tauri/launcher/index.html src-tauri/launcher/launcher.css src-tauri/launcher/launcher.js src-tauri/launcher/client.js src-tauri/launcher/*.test.mjs
git commit -m "fix: stabilize workflow shell"
```

If no fixes were needed, do not create an empty commit.

## Task 7: Update Product Notes

**Files:**
- Modify: `docs/rust_rewrite_parity_review.md`
- Modify: `docs/rust_iphone_workflow.md`

- [ ] **Step 1: Update parity review**

Add a completed-slice section:

```md
## Completed Slice: Workflow Shell

This slice split the first Rust client into Today, Capture, Process, and Settings workflows so the Mac and iPhone clients do not inherit a single overloaded dashboard.

Minimum scope delivered:

- Top-level workflow navigation.
- Settings-scoped server connection and auth guidance.
- Dedicated quick-capture workflow.
- Today workflow using the existing bootstrap summary.
- Process workflow using existing inbox routing and guided capture APIs.

Out of scope:

- New backend APIs.
- Full calendar editing.
- Weekly review.
- Offline sync.
- Physical iPhone signing.
```

- [ ] **Step 2: Update iPhone workflow note**

In `docs/rust_iphone_workflow.md`, note that the shared shell now implements the first workflow navigation shape, but still needs phone-specific refinement and physical-device testing.

- [ ] **Step 3: Commit docs**

```bash
git add docs/rust_rewrite_parity_review.md docs/rust_iphone_workflow.md
git commit -m "docs: record workflow shell progress"
```

## Final Verification

- [ ] **Step 1: Run final launcher verification**

```bash
node --test src-tauri/launcher/*.test.mjs
node --check src-tauri/launcher/launcher.js
node --check src-tauri/launcher/client.js
git status --short --branch
```

Expected:

- All launcher tests pass.
- JS syntax checks pass.
- Worktree contains only intentional committed changes, or is clean after final commit.

- [ ] **Step 2: Push branch**

```bash
git push origin codex/rust-rewrite
```

Expected: branch pushes to GitHub successfully.
