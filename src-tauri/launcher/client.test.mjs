import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_SERVER_URL,
  WORKFLOWS,
  buildConnectionGuidance,
  buildCaptureWorkflowViewModel,
  buildGuidedCapturePayload,
  buildGuidedCaptureFeedback,
  buildInboxActionFeedback,
  buildParkRoutePayload,
  buildProjectCardPayload,
  buildTodayTaskActionFeedback,
  buildWeeklyReviewActionFeedback,
  buildWeeklyReviewViewModel,
  buildInboxProcessingViewModel,
  buildProcessWorkflowViewModel,
  buildJsonHeaders,
  buildProjectOptions,
  buildBootstrapViewModel,
  defaultGuidedProjectTargetDate,
  guidedDecisionCopy,
  guidedProcessStepPlan,
  inferGuidedProjectCategory,
  getTauriInvoke,
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

test("settings round-trip through storage", async () => {
  const storage = memoryStorage();

  await saveSettings(storage, {
    serverUrl: " http://mac-mini.local:8088/ ",
    apiToken: " token ",
  });

  assert.deepEqual(await loadSettings(storage), {
    serverUrl: "http://mac-mini.local:8088",
    apiToken: "token",
  });
});

test("settings use native credential storage when Tauri invoke is available", async () => {
  const storage = memoryStorage({
    "sfo.rust.apiToken": " legacy-token ",
  });
  const calls = [];
  const invoke = async (command, payload) => {
    calls.push([command, payload]);
    return command === "get_api_token" ? "" : null;
  };

  const settings = await loadSettings(storage, invoke);

  assert.deepEqual(settings, {
    serverUrl: DEFAULT_SERVER_URL,
    apiToken: "legacy-token",
  });
  assert.deepEqual(calls, [
    ["get_api_token", undefined],
    ["set_api_token", { token: "legacy-token" }],
  ]);
  assert.equal(storage.getItem("sfo.rust.apiToken"), null);
});

test("saving settings writes tokens through native credential storage", async () => {
  const storage = memoryStorage({
    "sfo.rust.apiToken": "old-local-token",
  });
  const calls = [];
  const invoke = async (command, payload) => {
    calls.push([command, payload]);
    return null;
  };

  await saveSettings(
    storage,
    {
      serverUrl: "http://mac-mini.local:8088",
      apiToken: " secret-token ",
    },
    invoke,
  );

  assert.equal(storage.getItem("sfo.rust.serverUrl"), "http://mac-mini.local:8088");
  assert.equal(storage.getItem("sfo.rust.apiToken"), null);
  assert.deepEqual(calls, [["set_api_token", { token: "secret-token" }]]);

  await saveSettings(storage, { serverUrl: DEFAULT_SERVER_URL, apiToken: "" }, invoke);

  assert.deepEqual(calls.at(-1), ["clear_api_token", undefined]);
});

test("getTauriInvoke finds the global Tauri core invoke function", () => {
  const invoke = () => {};

  assert.equal(getTauriInvoke({ __TAURI__: { core: { invoke } } }), invoke);
  assert.equal(getTauriInvoke({}), null);
});

test("workflow metadata exposes the intended app paths", () => {
  assert.deepEqual(
    WORKFLOWS.map((workflow) => workflow.id),
    ["today", "capture", "process", "review", "settings"],
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

test("process workflow exposes only the active inbox item as actionable", () => {
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
    ["task-1"],
  );
});

test("process workflow handles an empty inbox", () => {
  const model = buildProcessWorkflowViewModel({ counts: {}, unprocessed: [] });

  assert.equal(model.activeItem, null);
  assert.equal(model.positionLabel, "Inbox clear");
  assert.deepEqual(model.queue, []);
});

test("weekly review view model exposes focus counts and review queues", () => {
  const model = buildWeeklyReviewViewModel(
    {
      review_date: "2026-05-10",
      week_starts_on: "2026-05-04",
      focus_counts: {
        work: { current: 3, cap: 4 },
        personal: { current: 2, cap: 3 },
      },
      weekly_projects: [
        {
          id: "p1",
          title: "Ship Rust review",
          category: "work",
          time_horizon: "week",
        },
      ],
      available_projects: [
        {
          id: "p1",
          title: "Ship Rust review",
          category: "work",
          active_this_week: true,
        },
        {
          id: "p2",
          title: "Family reset",
          category: "personal",
          active_this_week: false,
        },
      ],
      resurface_due: [
        {
          id: "t1",
          title: "Revisit parked task",
          when_bucket: "month",
          resurface_on: "2026-05-09",
        },
      ],
      completed_tasks: [
        {
          id: "t2",
          title: "Finished task",
          completed_at: "2026-05-10T08:00:00Z",
        },
      ],
    },
    {
      learning: [
        {
          id: "l1",
          verb_noun: "Read GTD article",
          description: "Maybe useful",
          created_at: "2026-05-09T08:00:00Z",
        },
      ],
      enjoy: [
        {
          id: "e1",
          verb_noun: "Watch film",
          created_at: "2026-05-08T08:00:00Z",
        },
      ],
      parked: [
        {
          id: "pk1",
          verb_noun: "Maybe buy scanner",
          created_at: "2026-05-07T08:00:00Z",
        },
      ],
      recycle_bin: [
        {
          id: "r1",
          verb_noun: "Old loose end",
          description: "No longer useful",
          created_at: "2026-05-06T08:00:00Z",
        },
      ],
    },
  );

  assert.equal(model.reviewLabel, "Week of Mon 4 May - Sun 10 May 2026");
  assert.equal(model.focusCounts.work.label, "3 / 4 work");
  assert.equal(model.weeklyProjects[0].title, "Ship Rust review");
  assert.equal(model.focusCandidates[1].toggleLabel, "Add to week");
  assert.equal(model.resurfaceDue[0].actionLabel, "Move to Week");
  assert.equal(model.completedTasks[0].actionLabel, "Archive");
  assert.equal(model.weeklyProjectsCountLabel, "1");
  assert.equal(model.focusCandidatesCountLabel, "2");
  assert.equal(model.resurfaceDueCountLabel, "1");
  assert.equal(model.completedTasksCountLabel, "1");
  assert.equal(model.learningItemsCountLabel, "1");
  assert.equal(model.enjoyItemsCountLabel, "1");
  assert.equal(model.parkedItemsCountLabel, "1");
  assert.equal(model.recycleBinItemsCountLabel, "1");
  assert.equal(model.learningItems[0].title, "Read GTD article");
  assert.equal(model.learningItems[0].meta, "Captured 2026-05-09");
  assert.equal(model.learningItems[0].description, "Maybe useful");
  assert.equal(model.enjoyItems[0].actionLabel, "Move to Inbox");
  assert.equal(model.parkedItems[0].title, "Maybe buy scanner");
  assert.equal(model.recycleBinItems[0].title, "Old loose end");
  assert.equal(model.recycleBinItems[0].description, "No longer useful");
  assert.equal(model.recycleBinItems[0].actionLabel, "Restore");
});

test("weekly review view model keeps routed review buckets empty by default", () => {
  const model = buildWeeklyReviewViewModel({});

  assert.deepEqual(model.learningItems, []);
  assert.deepEqual(model.enjoyItems, []);
  assert.deepEqual(model.parkedItems, []);
  assert.deepEqual(model.recycleBinItems, []);
  assert.equal(model.weeklyProjectsCountLabel, "0");
  assert.equal(model.focusCandidatesCountLabel, "0");
  assert.equal(model.resurfaceDueCountLabel, "0");
  assert.equal(model.completedTasksCountLabel, "0");
  assert.equal(model.learningItemsCountLabel, "0");
  assert.equal(model.enjoyItemsCountLabel, "0");
  assert.equal(model.parkedItemsCountLabel, "0");
  assert.equal(model.recycleBinItemsCountLabel, "0");
  assert.equal(model.emptyLearningItems, "No learning items parked.");
  assert.equal(model.emptyEnjoyItems, "No enjoy items parked.");
  assert.equal(model.emptyParkedItems, "No maybe-later items parked.");
  assert.equal(model.emptyRecycleBinItems, "Recycle Bin is empty.");
});

test("weekly review view model formats week ranges across month and year boundaries", () => {
  const monthBoundary = buildWeeklyReviewViewModel({
    week_starts_on: "2026-06-29",
  });
  const yearBoundary = buildWeeklyReviewViewModel({
    week_starts_on: "2025-12-29",
  });

  assert.equal(monthBoundary.reviewLabel, "Week of Mon 29 Jun - Sun 5 Jul 2026");
  assert.equal(yearBoundary.reviewLabel, "Week of Mon 29 Dec 2025 - Sun 4 Jan 2026");
});

test("weekly review routed item feedback supports restore and recycle", () => {
  assert.deepEqual(buildWeeklyReviewActionFeedback("restore-inbox-item", "Read article"), {
    message: "Moved Read article back to Inbox.",
    undo: null,
  });

  assert.deepEqual(buildWeeklyReviewActionFeedback("restore-recycled-item", "Old idea"), {
    message: "Restored Old idea to Inbox.",
    undo: null,
  });

  assert.deepEqual(buildWeeklyReviewActionFeedback("recycle-inbox-item", "Old idea"), {
    message: "Recycled Old idea.",
    undo: { label: "Restore", action: "restore-inbox-item" },
  });

  assert.deepEqual(buildWeeklyReviewActionFeedback("delete-recycled-item", "Old idea"), {
    message: "Deleted Old idea permanently.",
    undo: null,
  });
});

test("weekly review action feedback keeps irreversible move-to-week copy plain", () => {
  assert.deepEqual(buildWeeklyReviewActionFeedback("move-to-week", "Revisit parked task"), {
    message: "Moved Revisit parked task into this week.",
    undo: null,
  });
});

test("connection guidance treats loopback servers as simulator or Mac only", () => {
  const guidance = buildConnectionGuidance("http://127.0.0.1:8088", {
    authRequired: false,
    apiToken: "",
  });

  assert.deepEqual(guidance, {
    reachabilityLabel: "Simulator / this Mac",
    reachabilityDetail:
      "127.0.0.1 works from the iOS Simulator on this Mac, but a physical iPhone will not reach it. Use the Mac mini hostname or LAN IP on a real phone.",
    transportLabel: "Private HTTP",
    transportDetail:
      "HTTP is acceptable only on a trusted LAN or VPN while the prototype is private.",
    authLabel: "No token required",
    authDetail: "The server currently reports that bearer-token auth is off.",
    storageDetail:
      "This browser-only shell stores the token in local storage. The Tauri app stores it in Apple Keychain on macOS/iOS.",
    canPhoneReach: false,
  });
});

test("connection guidance reports native Apple Keychain storage when available", () => {
  const guidance = buildConnectionGuidance("http://mac-mini.local:8088", {
    nativeCredentialStorage: true,
  });

  assert.equal(
    guidance.storageDetail,
    "API tokens are stored in Apple Keychain on macOS/iOS through the Tauri app.",
  );
});

test("connection guidance reports auth as unknown before the server answers", () => {
  const guidance = buildConnectionGuidance("http://mac-mini.local:8088");

  assert.equal(guidance.authLabel, "Auth unknown");
  assert.equal(
    guidance.authDetail,
    "Connect to the server to confirm whether an API token is required.",
  );
});

test("connection guidance describes Mac mini LAN servers", () => {
  const guidance = buildConnectionGuidance("http://mac-mini.local:8088", {
    authRequired: true,
    apiToken: "secret",
  });

  assert.equal(guidance.reachabilityLabel, "LAN / VPN");
  assert.equal(
    guidance.reachabilityDetail,
    "Use this from iPhone only when the phone can reach the same private network name or VPN route.",
  );
  assert.equal(guidance.transportLabel, "Private HTTP");
  assert.equal(guidance.authLabel, "Token ready");
  assert.equal(guidance.canPhoneReach, true);
});

test("connection guidance distinguishes missing tokens and HTTPS endpoints", () => {
  const guidance = buildConnectionGuidance("https://sfo.example.com", {
    authRequired: true,
    apiToken: "",
  });

  assert.equal(guidance.reachabilityLabel, "Remote / routed");
  assert.equal(guidance.transportLabel, "HTTPS");
  assert.equal(
    guidance.transportDetail,
    "HTTPS is the right default if this server is reachable outside a trusted LAN.",
  );
  assert.equal(guidance.authLabel, "Token required");
  assert.equal(guidance.canPhoneReach, true);
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
      {
        id: "task-1",
        verb_noun: "Write shell tests",
        block_type: "focus",
        frog: true,
        status: "pending",
      },
      {
        id: "task-2",
        verb_noun: "Check docs",
        block_type: "admin",
        frog: false,
        status: "done",
        completed_at: "2026-05-06T09:45:00Z",
      },
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
  assert.equal(model.todayDisplayLabel, "Wed 6 May 2026 9:30AM");
  assert.equal(model.now.title, "Deep work");
  assert.equal(model.now.time, "09:00-10:30");
  assert.equal(model.inboxTotal, 2);
  assert.equal(model.routedInboxTotal, 8);
  assert.equal(model.recycleBinTotal, 5);
  assert.equal(model.todayTasks[0].meta, "focus · Frog");
  assert.equal(model.todayTasks[0].id, "task-1");
  assert.equal(model.todayTasks[0].completed, false);
  assert.equal(model.todayTasks[0].lifecycleAction, "complete");
  assert.equal(model.todayTasks[1].completed, true);
  assert.equal(model.todayTasks[1].lifecycleAction, "reopen");
  assert.equal(model.todayTasks[1].completedAt, "2026-05-06T09:45:00Z");
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

test("bootstrap view model formats Today label with weekday and AM/PM time", () => {
  const morning = buildBootstrapViewModel({
    today: "2026-05-13",
    current_time: "09:05:17.123456",
    inbox: {},
    rituals: {},
    waiting: {},
    system: {},
  });
  const evening = buildBootstrapViewModel({
    today: "2026-05-13",
    current_time: "17:50:00",
    inbox: {},
    rituals: {},
    waiting: {},
    system: {},
  });

  assert.equal(morning.todayDisplayLabel, "Wed 13 May 2026 9:05AM");
  assert.equal(evening.todayDisplayLabel, "Wed 13 May 2026 5:50PM");
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
    level_of_success: "moderate",
    why_link_text: "Make the trip calmer",
    first_chunk: "Draft options list",
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
    level_of_success: "moderate",
    why_link_text: "Make the trip calmer",
    first_chunk: "Draft options list",
    include_this_week: true,
    verb_check_ack: true,
    displacement_ack: true,
  });
});

test("project card payload preserves full shaping fields and trims success pack", () => {
  const payload = buildProjectCardPayload({
    title: "  Plan annual roadmap  ",
    description: " Shape it clearly ",
    category: "personal",
    status: "active",
    size: "",
    time_horizon: " quarter ",
    start_date: "2026-05-15",
    target_date: "2026-08-01",
    level_of_success: "epic",
    why_link_text: " Calmer month ",
    drag_points_notes: " Too many commitments ",
    gates_notes: " Use planning strengths ",
    budget_notes: " Two focus blocks ",
    active_this_week: "on",
    verb_check_ack: "",
    success_pack_guides: " Charlie ",
    success_pack_peers: " ",
    success_pack_supporters: " Morgan ",
    success_pack_beneficiaries: " Family ",
  });

  assert.deepEqual(payload, {
    title: "Plan annual roadmap",
    description: "Shape it clearly",
    category: "personal",
    status: "active",
    time_horizon: "quarter",
    start_date: "2026-05-15",
    target_date: "2026-08-01",
    level_of_success: "epic",
    why_link_text: "Calmer month",
    drag_points_notes: "Too many commitments",
    gates_notes: "Use planning strengths",
    budget_notes: "Two focus blocks",
    active_this_week: true,
    verb_check_ack: false,
    success_pack: {
      guides: "Charlie",
      peers: null,
      supporters: "Morgan",
      beneficiaries: "Family",
    },
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

test("park route payload supports optional date-time resurfacing", () => {
  assert.deepEqual(buildParkRoutePayload(""), {
    intent: "park_let_go",
  });
  assert.deepEqual(buildParkRoutePayload("2026-05-14T05:30:00Z"), {
    intent: "park_let_go",
    parked_until: "2026-05-14T05:30:00.000Z",
  });
  assert.throws(() => buildParkRoutePayload("not a date"), /valid date and time/);
});

test("today task action feedback exposes reversible lifecycle paths", () => {
  assert.deepEqual(
    buildTodayTaskActionFeedback({
      action: "complete",
      taskId: "task-1",
      taskTitle: "Write shell tests",
    }),
    {
      message: 'Completed "Write shell tests".',
      undoPath: "/api/v1/tasks/task-1/reopen",
      undoLabel: "Reopen",
      restoredMessage: 'Reopened "Write shell tests".',
    },
  );

  assert.deepEqual(
    buildTodayTaskActionFeedback({
      action: "reopen",
      taskId: "task-2",
      taskTitle: "",
    }),
    {
      message: 'Reopened "this task".',
      undoPath: "/api/v1/tasks/task-2/complete",
      undoLabel: "Complete",
      restoredMessage: 'Completed "this task".',
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

test("guided process step plan keeps clarification progressive", () => {
  const taskPlan = guidedProcessStepPlan("task");

  assert.deepEqual(
    taskPlan.map((step) => step.id),
    ["type", "describe", "details"],
  );
  assert.deepEqual(
    taskPlan.map((step) => step.label),
    ["Type", "Describe", "Plan"],
  );
  assert.match(taskPlan[2].description, /project and time/i);
});

test("guided process step plan tailors the final step by decision", () => {
  assert.equal(guidedProcessStepPlan("project")[2].label, "Shape");
  assert.match(guidedProcessStepPlan("project")[2].description, /category/i);

  assert.equal(guidedProcessStepPlan("opp")[2].label, "Owner");
  assert.match(guidedProcessStepPlan("opp")[2].description, /who owns/i);
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
