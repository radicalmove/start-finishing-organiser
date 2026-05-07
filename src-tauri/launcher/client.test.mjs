import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_SERVER_URL,
  buildGuidedCapturePayload,
  buildGuidedCaptureFeedback,
  buildInboxActionFeedback,
  buildInboxProcessingViewModel,
  buildJsonHeaders,
  buildProjectOptions,
  buildBootstrapViewModel,
  defaultGuidedProjectTargetDate,
  guidedDecisionCopy,
  inferGuidedProjectCategory,
  loadSettings,
  normalizeServerUrl,
  saveSettings,
} from "./client.js";

function memoryStorage(seed = {}) {
  const values = new Map(Object.entries(seed));
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    },
  };
}

test("normalizeServerUrl trims and removes trailing slashes", () => {
  assert.equal(normalizeServerUrl(" http://mac-mini.local:8088/// "), "http://mac-mini.local:8088");
});

test("normalizeServerUrl falls back to local Rust server when empty", () => {
  assert.equal(normalizeServerUrl(""), DEFAULT_SERVER_URL);
});

test("normalizeServerUrl rejects non-http protocols", () => {
  assert.throws(() => normalizeServerUrl("file:///tmp/sfo"), /http or https/);
});

test("buildJsonHeaders includes bearer token only when provided", () => {
  assert.deepEqual(buildJsonHeaders(""), {
    Accept: "application/json",
    "Content-Type": "application/json",
  });
  assert.deepEqual(buildJsonHeaders(" secret-token "), {
    Accept: "application/json",
    "Content-Type": "application/json",
    Authorization: "Bearer secret-token",
  });
});

test("settings round-trip through storage", () => {
  const storage = memoryStorage();

  saveSettings(storage, {
    serverUrl: " http://mac-mini.local:8088/ ",
    apiToken: " token ",
  });

  assert.deepEqual(loadSettings(storage), {
    serverUrl: "http://mac-mini.local:8088",
    apiToken: "token",
  });
});

test("bootstrap view model favors current work and bounded counts", () => {
  const model = buildBootstrapViewModel({
    today: "2026-05-06",
    current_time: "09:30:45.123456",
    weekly_projects: [{ title: "Ship client shell", category: "work" }],
    inbox: {
      unprocessed: 2,
      learn_explore: 1,
      enjoy_recover: 3,
      park_let_go: 4,
      recycle_bin: 5,
    },
    today_tasks: [
      { verb_noun: "Write shell tests", block_type: "focus", frog: true },
      { verb_noun: "Check docs", block_type: "admin", frog: false },
    ],
    today_blocks: [
      {
        title: "Deep work",
        start_time: "09:00:00",
        end_time: "10:30:00",
        block_type: "focus",
      },
    ],
    current_block: {
      title: "Deep work",
      start_time: "09:00:00",
      end_time: "10:30:00",
      block_type: "focus",
    },
    next_block: null,
    daily_focus: {
      one_thing: "Ship the Rust client shell",
      frog: "Make the first uncomfortable call",
    },
    rituals: {
      morning: true,
      midday: false,
      evening: false,
      next_key: "midday",
      next_label: "Midday reset",
    },
    waiting: {
      total: 2,
      due: 1,
      overdue: 0,
    },
    system: {
      database_status: "ok",
      schema: "sfo-rust-foundation",
      import_supported_tables: ["projects", "tasks"],
      backup_tables: [],
    },
  });

  assert.equal(model.todayLabel, "2026-05-06");
  assert.equal(model.currentTime, "09:30");
  assert.equal(model.now.title, "Deep work");
  assert.equal(model.now.time, "09:00-10:30");
  assert.equal(model.inboxTotal, 15);
  assert.equal(model.todayTasks[0].meta, "focus · Frog");
  assert.equal(model.weeklyProjects[0].title, "Ship client shell");
  assert.equal(model.dailyFocus.oneThing, "Ship the Rust client shell");
  assert.equal(model.dailyFocus.frog, "Make the first uncomfortable call");
  assert.equal(model.rituals.nextLabel, "Midday reset");
  assert.equal(model.waiting.label, "1 due");
});

test("bootstrap view model falls back to daily focus when no block is active", () => {
  const model = buildBootstrapViewModel({
    today: "2026-05-06",
    current_time: "14:30:00",
    weekly_projects: [],
    inbox: {},
    today_tasks: [],
    today_blocks: [],
    current_block: null,
    next_block: null,
    daily_focus: {
      one_thing: "Write proposal",
      frog: "Call the supplier",
    },
    rituals: {},
    waiting: {},
    system: {},
  });

  assert.equal(model.now.title, "Write proposal");
  assert.equal(model.now.meta, "One Thing");
  assert.equal(model.dailyFocus.frog, "Call the supplier");
});

test("inbox processing view model exposes actionable unprocessed items", () => {
  const model = buildInboxProcessingViewModel({
    counts: {
      unprocessed: 2,
      learn_explore: 1,
      enjoy_recover: 0,
      park_let_go: 3,
      recycle_bin: 4,
    },
    unprocessed: [
      {
        id: "task-1",
        verb_noun: "Read Rust notes",
        description: "Extract anything worth testing",
        created_at: "2026-05-06T09:00:00Z",
      },
      {
        id: "task-2",
        verb_noun: "",
        description: null,
        created_at: null,
      },
    ],
  });

  assert.equal(model.pendingCount, 2);
  assert.equal(model.recycledCount, 4);
  assert.deepEqual(model.items[0], {
    id: "task-1",
    title: "Read Rust notes",
    description: "Extract anything worth testing",
    meta: "Captured 2026-05-06T09:00:00Z",
  });
  assert.equal(model.items[1].title, "Untitled inbox item");
});

test("project options preserve active project ids and labels", () => {
  const options = buildProjectOptions({
    items: [
      { id: "project-1", title: "Ship Rust shell", category: "work", active_this_week: true },
      { id: "project-2", title: "", category: "personal", active_this_week: false },
    ],
  });

  assert.deepEqual(options, [
    { id: "project-1", label: "Ship Rust shell · work · this week" },
    { id: "project-2", label: "Untitled project · personal" },
  ]);
});

test("guided capture payload converts an inbox item into a project task", () => {
  const payload = buildGuidedCapturePayload("task", "task-1", {
    capture_text: "Draft Rust wizard",
    description: "Use existing guided API",
    project_id: "project-1",
    horizon: "month",
    block_type: "focus",
    duration_minutes: "45",
    frog: "on",
    displacement_ack: "on",
  });

  assert.deepEqual(payload, {
    capture_text: "Draft Rust wizard",
    description: "Use existing guided API",
    item_kind: "task",
    source_task_id: "task-1",
    inbox_intent: "support_project",
    project_id: "project-1",
    horizon: "month",
    block_type: "focus",
    duration_minutes: 45,
    frog: true,
    owner_type: "mine",
    displacement_ack: true,
  });
});

test("guided capture payload converts an inbox item into a project", () => {
  const payload = buildGuidedCapturePayload("project", "task-1", {
    capture_text: "Plan family trip",
    description: "",
    category: "personal",
    horizon: "quarter",
    target_date: "2026-08-01",
    include_this_week: "on",
    verb_check_ack: "on",
    displacement_ack: "on",
  });

  assert.deepEqual(payload, {
    capture_text: "Plan family trip",
    item_kind: "project",
    source_task_id: "task-1",
    inbox_intent: "support_project",
    category: "personal",
    horizon: "quarter",
    target_date: "2026-08-01",
    include_this_week: true,
    verb_check_ack: true,
    displacement_ack: true,
  });
});

test("guided capture payload converts an inbox item into an opp waiting item", () => {
  const payload = buildGuidedCapturePayload("opp", "task-1", {
    capture_text: "Review Sam's budget",
    project_id: "project-1",
    horizon: "week",
    waiting_person: "Sam",
    displacement_ack: "on",
  });

  assert.deepEqual(payload, {
    capture_text: "Review Sam's budget",
    item_kind: "task",
    source_task_id: "task-1",
    inbox_intent: "support_project",
    project_id: "project-1",
    horizon: "week",
    owner_type: "opp",
    waiting_person: "Sam",
    displacement_ack: true,
  });
});

test("guided project target date defaults to the server today value", () => {
  assert.equal(defaultGuidedProjectTargetDate("2026-05-06"), "2026-05-06");
  assert.equal(
    defaultGuidedProjectTargetDate("Today", new Date("2026-05-07T02:00:00Z")),
    "2026-05-07",
  );
});

test("inbox action feedback exposes undo paths for reversible actions", () => {
  assert.deepEqual(
    buildInboxActionFeedback({
      action: "route",
      itemId: "task-1",
      itemTitle: "Read Rust notes",
      intentLabel: "Learning",
    }),
    {
      message: 'Moved "Read Rust notes" to Learning.',
      undoPath: "/api/v1/inbox/task-1/undo",
      undoLabel: "Undo",
      restoredMessage: 'Restored "Read Rust notes" to Inbox.',
    },
  );

  assert.deepEqual(
    buildInboxActionFeedback({
      action: "recycle",
      itemId: "task-2",
      itemTitle: "",
    }),
    {
      message: 'Moved "this item" to Recycle.',
      undoPath: "/api/v1/inbox/task-2/restore",
      undoLabel: "Restore",
      restoredMessage: 'Restored "this item" to Inbox.',
    },
  );
});

test("guided capture feedback describes non-reversible conversions", () => {
  assert.deepEqual(buildGuidedCaptureFeedback("opp", "Ask Sam"), {
    message: 'Converted "Ask Sam" into a Waiting On item.',
    undoPath: "",
    undoLabel: "",
    restoredMessage: "",
  });
  assert.equal(
    buildGuidedCaptureFeedback("project", "").message,
    'Converted "this item" into a project.',
  );
});

test("guided decision copy explains the active choice", () => {
  assert.deepEqual(guidedDecisionCopy("task"), {
    heading: "Make it a task",
    description: "Attach it to an existing project so it becomes planned work, not loose backlog.",
    submitLabel: "Create task",
  });
  assert.deepEqual(guidedDecisionCopy("project"), {
    heading: "Start a project",
    description: "Use this when the item needs more than one step or deserves weekly attention.",
    submitLabel: "Create project",
  });
  assert.equal(guidedDecisionCopy("opp").submitLabel, "Create Waiting On");
});

test("guided project category defaults personal for obvious personal captures", () => {
  assert.equal(
    inferGuidedProjectCategory("Book optometrist appointment", "This is probably personal."),
    "personal",
  );
  assert.equal(
    inferGuidedProjectCategory("Plan winter family rhythm", ""),
    "personal",
  );
  assert.equal(
    inferGuidedProjectCategory("Ship Rust client review", "Use existing shell."),
    "work",
  );
});
