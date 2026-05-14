export const DEFAULT_SERVER_URL = "http://127.0.0.1:8088";

const SERVER_URL_KEY = "sfo.rust.serverUrl";
const API_TOKEN_KEY = "sfo.rust.apiToken";
const PERSONAL_PROJECT_PATTERN =
  /\b(appointment|optometrist|doctor|dentist|health|family|home|house|kid|kids|school|holiday|trip|birthday|personal|exercise|training|winter family)\b/i;

export const WORKFLOWS = [
  { id: "today", label: "Today" },
  { id: "capture", label: "Capture" },
  { id: "process", label: "Process" },
  { id: "review", label: "Review" },
  { id: "settings", label: "Settings" },
];

export function normalizeServerUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return DEFAULT_SERVER_URL;

  let url;
  try {
    url = new URL(raw);
  } catch (err) {
    throw new Error("Server URL must be a valid URL");
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("Server URL must use http or https");
  }

  return url.toString().replace(/\/+$/, "");
}

export function buildApiUrl(serverUrl, path) {
  const base = normalizeServerUrl(serverUrl);
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export function buildJsonHeaders(apiToken) {
  const headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  const token = String(apiToken || "").trim();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export function getTauriInvoke(globalObject = globalThis) {
  return globalObject?.__TAURI__?.core?.invoke || null;
}

export async function loadSettings(storage, invoke = null) {
  const legacyToken = String(storage?.getItem(API_TOKEN_KEY) || "").trim();
  let apiToken = legacyToken;

  if (invoke) {
    apiToken = String((await invoke("get_api_token")) || "").trim();
    if (!apiToken && legacyToken) {
      await invoke("set_api_token", { token: legacyToken });
      apiToken = legacyToken;
    }
    storage?.removeItem(API_TOKEN_KEY);
  }

  return {
    serverUrl: normalizeServerUrl(storage?.getItem(SERVER_URL_KEY) || DEFAULT_SERVER_URL),
    apiToken,
  };
}

export async function saveSettings(storage, settings, invoke = null) {
  storage?.setItem(SERVER_URL_KEY, normalizeServerUrl(settings.serverUrl));
  const token = String(settings.apiToken || "").trim();
  if (invoke) {
    if (token) {
      await invoke("set_api_token", { token });
    } else {
      await invoke("clear_api_token");
    }
    storage?.removeItem(API_TOKEN_KEY);
    return;
  }

  if (token) {
    storage?.setItem(API_TOKEN_KEY, token);
  } else {
    storage?.removeItem(API_TOKEN_KEY);
  }
}

export async function clearSettings(storage, invoke = null) {
  storage?.removeItem(SERVER_URL_KEY);
  storage?.removeItem(API_TOKEN_KEY);
  if (invoke) {
    await invoke("clear_api_token");
  }
}

export function buildConnectionGuidance(serverUrl, options = {}) {
  const normalized = normalizeServerUrl(serverUrl);
  const url = new URL(normalized);
  const host = url.hostname.toLowerCase().replace(/^\[(.*)\]$/, "$1");
  const loopback = isLoopbackHost(host);
  const privateNetwork = isPrivateNetworkHost(host);
  const localName = host.endsWith(".local") || (!host.includes(".") && !loopback);

  let reachabilityLabel = "Remote / routed";
  let reachabilityDetail =
    "Use this from iPhone only if routing, firewall, and server binding are deliberately configured.";
  let canPhoneReach = true;

  if (loopback) {
    reachabilityLabel = "Simulator / this Mac";
    reachabilityDetail =
      "127.0.0.1 works from the iOS Simulator on this Mac, but a physical iPhone will not reach it. Use the Mac mini hostname or LAN IP on a real phone.";
    canPhoneReach = false;
  } else if (privateNetwork || localName) {
    reachabilityLabel = "LAN / VPN";
    reachabilityDetail =
      "Use this from iPhone only when the phone can reach the same private network name or VPN route.";
  }

  const transportIsHttps = url.protocol === "https:";
  const authKnown =
    Object.prototype.hasOwnProperty.call(options, "authRequired") && options.authRequired !== null;
  const authRequired = options.authRequired === true;
  const tokenPresent = Boolean(String(options.apiToken || "").trim());

  return {
    reachabilityLabel,
    reachabilityDetail,
    transportLabel: transportIsHttps ? "HTTPS" : "Private HTTP",
    transportDetail: transportIsHttps
      ? "HTTPS is the right default if this server is reachable outside a trusted LAN."
      : "HTTP is acceptable only on a trusted LAN or VPN while the prototype is private.",
    authLabel: authKnown
      ? authRequired
        ? tokenPresent
          ? "Token ready"
          : "Token required"
        : "No token required"
      : "Auth unknown",
    authDetail: authKnown
      ? authRequired
        ? tokenPresent
          ? "The server requires bearer-token auth and this shell has a token to send."
          : "The server requires bearer-token auth. Add the API token before loading private data."
        : "The server currently reports that bearer-token auth is off."
      : "Connect to the server to confirm whether an API token is required.",
    storageDetail: options.nativeCredentialStorage
      ? "API tokens are stored in Apple Keychain on macOS/iOS through the Tauri app."
      : "This browser-only shell stores the token in local storage. The Tauri app stores it in Apple Keychain on macOS/iOS.",
    canPhoneReach,
  };
}

export async function requestJson(fetchImpl, settings, path, options = {}) {
  const method = options.method || "GET";
  const body = options.body === undefined ? undefined : JSON.stringify(options.body);
  const response = await fetchImpl(buildApiUrl(settings.serverUrl, path), {
    method,
    cache: "no-store",
    headers: buildJsonHeaders(settings.apiToken),
    body,
  });

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (err) {
      payload = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.status || `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return payload;
}

export function buildSearchApiPath(query, includeRecycleBin = false) {
  const text = String(query || "").trim();
  if (!text) return "";

  const params = new URLSearchParams();
  params.set("q", text);
  if (includeRecycleBin) {
    params.set("include_recycle_bin", "true");
  }
  return `/api/v1/search?${params.toString()}`;
}

export function buildItemDetailApiPath(item = {}) {
  const id = String(item.id || "").trim();
  if (!id) return "";

  const encodedId = encodeURIComponent(id);
  if (item.kind === "project") {
    return `/api/v1/projects/${encodedId}/card`;
  }
  if (item.kind === "task" || item.kind === "recycle_bin") {
    return `/api/v1/tasks/${encodedId}`;
  }
  if (item.kind === "waiting") {
    return `/api/v1/waiting/${encodedId}`;
  }
  return "";
}

export function buildGlobalSearchViewModel(payload = {}) {
  const query = String(payload.query || "").trim();
  const items = (payload.items || []).map(searchResultView);
  const groups = [];
  for (const kind of ["project", "task", "waiting", "recycle_bin"]) {
    const groupItems = items.filter((item) => item.kind === kind);
    if (groupItems.length) {
      groups.push({
        kind,
        label: searchGroupLabel(kind),
        items: groupItems,
      });
    }
  }

  return {
    query,
    includeRecycleBin: Boolean(payload.include_recycle_bin),
    hasQuery: Boolean(query),
    items,
    groups,
    totalCountLabel: `${items.length} ${items.length === 1 ? "result" : "results"}`,
    emptyText: query ? "No matching SFO items." : "Type to search SFO.",
  };
}

export function buildItemDetailViewModel(item = {}, detailPayload = null) {
  const enrichedItem = mergeItemDetailPayload(item, detailPayload);
  const result = searchResultView(enrichedItem);
  const workflowLabel = workflowDisplayLabel(result.workflow);
  const rows = [
    { label: "Type", value: itemKindLabel(result.kind) },
    { label: "Location", value: result.badge },
    ...richItemDetailRows(enrichedItem, detailPayload),
    { label: "Captured", value: formatSearchTimestamp(result.createdAt) },
  ].filter((row) => row.value);

  return {
    id: result.id,
    kind: result.kind,
    kindLabel: itemKindLabel(result.kind),
    title: result.title,
    description: result.description,
    badge: result.badge,
    recycled: result.recycled,
    workflow: result.workflow,
    workflowLabel,
    actionLabel: `Open in ${workflowLabel}`,
    actions: buildItemDetailActions({ ...enrichedItem, ...result, workflowLabel }),
    rows,
  };
}

export function buildItemDetailActions(detail = {}) {
  const id = String(detail.id || "").trim();
  const encodedId = encodeURIComponent(id);
  const workflow = detail.workflow || "today";
  const workflowLabel = detail.workflowLabel || workflowDisplayLabel(workflow);
  const actions = [];

  if (id && detail.kind === "project") {
    actions.push({
      id: "open-shape-card",
      label: "Open Shape Card",
      workflow: "review",
      projectId: id,
      primary: true,
    });
  } else if (id && detail.kind === "waiting") {
    actions.push({
      id: "resolve-waiting",
      label: "Resolve",
      path: `/api/v1/waiting/${encodedId}/resolve`,
      method: "POST",
      primary: true,
    });
  } else if (id && (detail.kind === "recycle_bin" || detail.recycled)) {
    actions.push({
      id: "restore-task",
      label: "Restore",
      path: `/api/v1/tasks/${encodedId}/restore`,
      method: "POST",
      primary: true,
    });
  } else if (id && detail.kind === "task") {
    const done = detail.status === "done" || Boolean(detail.completed_at || detail.completedAt);
    actions.push({
      id: done ? "reopen-task" : "complete-task",
      label: done ? "Reopen" : "Complete",
      path: `/api/v1/tasks/${encodedId}/${done ? "reopen" : "complete"}`,
      method: "POST",
      primary: true,
    });
  }

  actions.push({
    id: "open-workflow",
    label: `Open in ${workflowLabel}`,
    workflow,
    primary: !actions.length,
  });

  return actions;
}

export function buildBootstrapViewModel(summary) {
  const todayLabel = summary?.today || "Today";
  const currentTime = trimSeconds(summary?.current_time || "");
  const inbox = summary?.inbox || {};
  const weeklyProjects = (summary?.weekly_projects || []).map((project) => ({
    id: project.id || "",
    kind: "project",
    title: project.title || "Untitled project",
    description: project.description || project.why_link_text || "",
    meta: compactJoin([project.category, project.time_horizon]),
    location: "Project",
    createdAt: project.created_at || project.createdAt || "",
  }));
  const todayTasks = (summary?.today_tasks || []).map((task) => {
    const completed = task.status === "done" || Boolean(task.completed_at);
    return {
      id: task.id || "",
      kind: "task",
      title: task.verb_noun || "Untitled task",
      description: task.description || "",
      meta: compactJoin([
        task.block_type,
        task.frog ? "Frog" : "",
        task.alignment,
      ]),
      location: "Today",
      createdAt: task.created_at || task.createdAt || "",
      status: task.status || "pending",
      completed,
      completedAt: task.completed_at || "",
      lifecycleAction: completed ? "reopen" : "complete",
      lifecycleLabel: completed ? "Reopen" : "Complete",
    };
  });
  const todayBlocks = (summary?.today_blocks || []).map(blockView);
  const dailyFocus = {
    oneThing: summary?.daily_focus?.one_thing || "",
    frog: summary?.daily_focus?.frog || "",
  };
  const waiting = {
    total: Number(summary?.waiting?.total || 0),
    due: Number(summary?.waiting?.due || 0),
    overdue: Number(summary?.waiting?.overdue || 0),
  };
  waiting.label = waiting.overdue
    ? `${waiting.overdue} overdue`
    : waiting.due
      ? `${waiting.due} due`
      : `${waiting.total} waiting`;

  return {
    todayLabel,
    currentTime,
    todayDisplayLabel: formatTodayDisplayLabel(todayLabel, currentTime),
    inbox,
    inboxTotal: Number(inbox.unprocessed || 0),
    routedInboxTotal:
      Number(inbox.learn_explore || 0) +
      Number(inbox.enjoy_recover || 0) +
      Number(inbox.park_let_go || 0),
    recycleBinTotal: Number(inbox.recycle_bin || 0),
    weeklyProjects,
    todayTasks,
    todayBlocks,
    now: summary?.current_block
      ? blockView(summary.current_block)
      : dailyFocus.oneThing
        ? {
            title: dailyFocus.oneThing,
            time: "",
            meta: "One Thing",
          }
        : dailyFocus.frog
          ? {
              title: dailyFocus.frog,
              time: "",
              meta: "Frog",
            }
          : {
              title: "No block active",
              time: "",
              meta: "Choose the next protected block.",
            },
    next: summary?.next_block ? blockView(summary.next_block) : null,
    dailyFocus,
    rituals: {
      morning: Boolean(summary?.rituals?.morning),
      midday: Boolean(summary?.rituals?.midday),
      evening: Boolean(summary?.rituals?.evening),
      nextKey: summary?.rituals?.next_key || "",
      nextLabel: summary?.rituals?.next_label || "",
    },
    waiting,
    systemStatus: summary?.system?.database_status || "unknown",
    schema: summary?.system?.schema || "",
  };
}

export function buildInboxProcessingViewModel(containers) {
  const counts = containers?.counts || {};
  const items = (containers?.unprocessed || []).map((item) => ({
    id: item.id,
    title: item.verb_noun || "Untitled inbox item",
    description: item.description || "No notes yet.",
    meta: item.created_at ? `Captured ${item.created_at}` : "",
  }));

  return {
    pendingCount: Number(counts.unprocessed || 0),
    recycledCount: Number(counts.recycle_bin || 0),
    items,
  };
}

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
    queue: activeItem ? [activeItem] : [],
    positionLabel: activeItem ? `${safeIndex + 1} of ${base.items.length}` : "Inbox clear",
  };
}

export function buildProjectOptions(projectPage) {
  return (projectPage?.items || []).map((project) => ({
    id: project.id,
    label: compactJoin([
      project.title || "Untitled project",
      project.category,
      project.active_this_week ? "this week" : "",
    ]),
  }));
}

export function buildWeeklyReviewViewModel(summary, inboxContainers = {}) {
  const workCount = focusCountView(summary?.focus_counts?.work, "work");
  const personalCount = focusCountView(summary?.focus_counts?.personal, "personal");
  const weeklyProjects = (summary?.weekly_projects || []).map(reviewProjectView);
  const focusCandidates = (summary?.available_projects || []).map((project) => {
    const active = Boolean(project.active_this_week);
    return {
      ...reviewProjectView(project),
      active,
      toggleLabel: active ? "Drop from week" : "Add to week",
      nextActive: !active,
    };
  });
  const resurfaceDue = (summary?.resurface_due || []).map((task) =>
    reviewTaskView(task, "Move to Week"),
  );
  const completedTasks = (summary?.completed_tasks || []).map((task) =>
    reviewTaskView(task, "Archive"),
  );
  const learningItems = (inboxContainers?.learning || []).map((item) =>
    routedInboxItemView(item, "Learning"),
  );
  const enjoyItems = (inboxContainers?.enjoy || []).map((item) =>
    routedInboxItemView(item, "Enjoy"),
  );
  const parkedItems = (inboxContainers?.parked || []).map((item) =>
    routedInboxItemView(item, "Parked"),
  );
  const recycleBinItems = (inboxContainers?.recycle_bin || []).map(recycleBinItemView);

  return {
    reviewDate: summary?.review_date || "",
    weekStartsOn: summary?.week_starts_on || "",
    reviewLabel: summary?.week_starts_on
      ? `Week of ${formatWeekRangeDisplayLabel(summary.week_starts_on)}`
      : "Weekly Review",
    focusCounts: {
      work: workCount,
      personal: personalCount,
    },
    weeklyProjects,
    focusCandidates,
    resurfaceDue,
    completedTasks,
    learningItems,
    enjoyItems,
    parkedItems,
    recycleBinItems,
    weeklyProjectsCountLabel: countLabel(weeklyProjects),
    focusCandidatesCountLabel: countLabel(focusCandidates),
    resurfaceDueCountLabel: countLabel(resurfaceDue),
    completedTasksCountLabel: countLabel(completedTasks),
    learningItemsCountLabel: countLabel(learningItems),
    enjoyItemsCountLabel: countLabel(enjoyItems),
    parkedItemsCountLabel: countLabel(parkedItems),
    recycleBinItemsCountLabel: countLabel(recycleBinItems),
    emptyWeeklyProjects: "No weekly projects selected.",
    emptyFocusCandidates: "No active projects available to add.",
    emptyResurfaceDue: "No due resurfacing tasks.",
    emptyCompletedTasks: "No completed tasks to archive this week.",
    emptyLearningItems: "No learning items parked.",
    emptyEnjoyItems: "No enjoy items parked.",
    emptyParkedItems: "No maybe-later items parked.",
    emptyRecycleBinItems: "Recycle Bin is empty.",
  };
}

export function buildWeeklyReviewActionFeedback(action, title) {
  const itemTitle = displayItemTitle(title);
  if (action === "restore-inbox-item") {
    return {
      message: `Moved ${itemTitle} back to Inbox.`,
      undo: null,
    };
  }
  if (action === "restore-recycled-item") {
    return {
      message: `Restored ${itemTitle} to Inbox.`,
      undo: null,
    };
  }
  if (action === "recycle-inbox-item") {
    return {
      message: `Recycled ${itemTitle}.`,
      undo: { label: "Restore", action: "restore-inbox-item" },
    };
  }
  if (action === "delete-recycled-item") {
    return {
      message: `Deleted ${itemTitle} permanently.`,
      undo: null,
    };
  }
  if (action === "move-to-week") {
    return {
      message: `Moved ${itemTitle} into this week.`,
      undo: null,
    };
  }
  if (action === "archive") {
    return {
      message: `Archived ${itemTitle}.`,
      undo: { label: "Restore", action: "restore-task" },
    };
  }
  if (action === "focus-off") {
    return {
      message: `Dropped ${itemTitle} from this week.`,
      undo: null,
    };
  }
  return {
    message: `Added ${itemTitle} to this week.`,
    undo: null,
  };
}

export function buildGuidedCapturePayload(decision, sourceTaskId, values) {
  const title = optionalText(values.capture_text) || "";
  const payload = {
    capture_text: title,
    item_kind: decision === "project" ? "project" : "task",
    source_task_id: sourceTaskId,
    inbox_intent: "support_project",
    horizon: values.horizon || "week",
    displacement_ack: Boolean(values.displacement_ack),
  };

  setOptional(payload, "description", values.description);

  if (decision === "project") {
    payload.category = values.category || "work";
    setOptional(payload, "target_date", values.target_date);
    setOptional(payload, "level_of_success", values.level_of_success);
    setOptional(payload, "why_link_text", values.why_link_text);
    setOptional(payload, "first_chunk", values.first_chunk);
    payload.include_this_week = Boolean(values.include_this_week);
    payload.verb_check_ack = Boolean(values.verb_check_ack);
    return payload;
  }

  setOptional(payload, "project_id", values.project_id);
  setOptional(payload, "block_type", values.block_type);
  const duration = positiveInteger(values.duration_minutes);
  if (duration) {
    payload.duration_minutes = duration;
  }
  if (values.frog) {
    payload.frog = true;
  }

  if (decision === "opp") {
    payload.owner_type = "opp";
    setOptional(payload, "waiting_person", values.waiting_person);
  } else {
    payload.owner_type = "mine";
  }

  return payload;
}

export function buildProjectCardPayload(values) {
  const payload = {
    title: optionalText(values.title) || "",
    category: optionalText(values.category) || "work",
    status: optionalText(values.status) || "active",
    active_this_week: checkboxValue(values.active_this_week),
    verb_check_ack: checkboxValue(values.verb_check_ack),
    success_pack: {
      guides: optionalText(values.success_pack_guides),
      peers: optionalText(values.success_pack_peers),
      supporters: optionalText(values.success_pack_supporters),
      beneficiaries: optionalText(values.success_pack_beneficiaries),
    },
  };

  setOptional(payload, "description", values.description);
  setOptional(payload, "size", values.size);
  setOptional(payload, "time_horizon", values.time_horizon);
  setOptional(payload, "start_date", values.start_date);
  setOptional(payload, "target_date", values.target_date);
  setOptional(payload, "level_of_success", values.level_of_success);
  setOptional(payload, "why_link_text", values.why_link_text);
  setOptional(payload, "drag_points_notes", values.drag_points_notes);
  setOptional(payload, "gates_notes", values.gates_notes);
  setOptional(payload, "budget_notes", values.budget_notes);

  return payload;
}

export function guidedDecisionCopy(decision) {
  if (decision === "project") {
    return {
      heading: "Start a project",
      description: "Use this when the item needs more than one step or deserves weekly attention.",
      submitLabel: "Create project",
    };
  }
  if (decision === "opp") {
    return {
      heading: "Track a Waiting On",
      description: "Use this when somebody else owns the next move and you need a follow-up.",
      submitLabel: "Create Waiting On",
    };
  }
  return {
    heading: "Make it a task",
    description: "Attach it to an existing project so it becomes planned work, not loose backlog.",
    submitLabel: "Create task",
  };
}

export function guidedProcessStepPlan(decision) {
  const detailsStep =
    decision === "project"
      ? {
          id: "details",
          label: "Shape",
          heading: "Shape the project",
          description: "Set category, target date, and whether this belongs in the current week.",
        }
      : decision === "opp"
        ? {
            id: "details",
            label: "Owner",
            heading: "Name the owner",
            description: "Choose the related project, who owns the next move, and save.",
          }
        : {
            id: "details",
            label: "Plan",
            heading: "Plan the task",
            description: "Choose project and time details, then save the decision.",
          };

  return [
    {
      id: "type",
      label: "Type",
      heading: "Choose the right shape",
      description: "Decide whether this is your task, a project, or something you are waiting on.",
    },
    {
      id: "describe",
      label: "Describe",
      heading: "Confirm title and notes",
      description: "Keep only the context needed to make the next decision clear.",
    },
    detailsStep,
  ];
}

export function inferGuidedProjectCategory(itemTitle, itemDescription = "") {
  const text = `${itemTitle || ""} ${itemDescription || ""}`;
  return PERSONAL_PROJECT_PATTERN.test(text) ? "personal" : "work";
}

export function buildInboxActionFeedback({ action, itemId, itemTitle, intentLabel = "" }) {
  const title = displayItemTitle(itemTitle);
  const encodedItemId = encodeURIComponent(String(itemId || ""));
  if (action === "route") {
    return {
      message: `Moved "${title}" to ${intentLabel || "its container"}.`,
      undoPath: encodedItemId ? `/api/v1/inbox/${encodedItemId}/undo` : "",
      undoLabel: "Undo",
      restoredMessage: `Restored "${title}" to Inbox.`,
    };
  }

  return {
    message: `Moved "${title}" to Recycle.`,
    undoPath: encodedItemId ? `/api/v1/inbox/${encodedItemId}/restore` : "",
    undoLabel: "Restore",
    restoredMessage: `Restored "${title}" to Inbox.`,
  };
}

export function buildParkRoutePayload(parkedUntilValue = "") {
  const payload = {
    intent: "park_let_go",
  };
  const parkedUntil = String(parkedUntilValue || "").trim();
  if (!parkedUntil) return payload;

  const date = new Date(parkedUntil);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Choose a valid date and time.");
  }

  payload.parked_until = date.toISOString();
  return payload;
}

export function buildTodayTaskActionFeedback({ action, taskId, taskTitle }) {
  const title = displayTaskTitle(taskTitle);
  const encodedTaskId = encodeURIComponent(String(taskId || ""));
  if (action === "reopen") {
    return {
      message: `Reopened "${title}".`,
      undoPath: encodedTaskId ? `/api/v1/tasks/${encodedTaskId}/complete` : "",
      undoLabel: "Complete",
      restoredMessage: `Completed "${title}".`,
    };
  }

  return {
    message: `Completed "${title}".`,
    undoPath: encodedTaskId ? `/api/v1/tasks/${encodedTaskId}/reopen` : "",
    undoLabel: "Reopen",
    restoredMessage: `Reopened "${title}".`,
  };
}

export function buildGuidedCaptureFeedback(decision, itemTitle) {
  const title = displayItemTitle(itemTitle);
  const noun =
    decision === "project"
      ? "a project"
      : decision === "opp"
        ? "a Waiting On item"
        : "a project task";
  return {
    message: `Converted "${title}" into ${noun}.`,
    undoPath: "",
    undoLabel: "",
    restoredMessage: "",
  };
}

export function defaultGuidedProjectTargetDate(todayLabel, fallbackDate = new Date()) {
  const value = String(todayLabel || "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }
  return fallbackDate.toISOString().slice(0, 10);
}

function blockView(block) {
  return {
    title: block.title || titleCase(`${block.block_type || "time"} block`),
    time: compactJoin([trimSeconds(block.start_time), trimSeconds(block.end_time)], "-"),
    meta: titleCase(block.block_type || ""),
  };
}

function focusCountView(count, fallbackCategory) {
  const current = Number(count?.current || 0);
  const cap = Number(count?.cap || 0);
  const category = count?.category || fallbackCategory;
  return {
    category,
    current,
    cap,
    label: `${current} / ${cap} ${category}`,
    atCap: cap > 0 && current >= cap,
  };
}

function reviewProjectView(project) {
  return {
    id: project.id || "",
    kind: "project",
    title: project.title || "Untitled project",
    meta: compactJoin([
      project.category,
      project.time_horizon,
      project.target_date ? `target ${project.target_date}` : "",
    ]),
    description: project.description || project.why_link_text || "",
    category: project.category || "",
    location: "Project",
    createdAt: project.created_at || project.createdAt || "",
  };
}

function searchResultView(item) {
  const kind = item.kind || "task";
  const location = item.location || searchGroupLabel(kind);
  const recycled = Boolean(item.recycled);
  return {
    id: item.id || "",
    kind,
    title: item.title || "Untitled item",
    description: item.description || "",
    location,
    recycled,
    badge: recycled ? "Recycle Bin" : location,
    workflow: searchResultWorkflow(kind, location),
    createdAt: item.created_at || item.createdAt || "",
  };
}

function mergeItemDetailPayload(item, payload) {
  if (!payload) return item;

  if (payload.project) {
    const project = payload.project || {};
    return {
      ...item,
      ...project,
      id: project.id || item.id || "",
      kind: "project",
      title: project.title || item.title || "Untitled project",
      description: project.description || project.why_link_text || item.description || "",
      location: item.location || "Project",
      createdAt: project.created_at || project.createdAt || item.createdAt || "",
      roadmapChunksCount: Array.isArray(payload.chunks) ? payload.chunks.length : null,
    };
  }

  if (payload.verb_noun || payload.when_bucket || payload.status) {
    return {
      ...item,
      ...payload,
      id: payload.id || item.id || "",
      kind: item.kind === "recycle_bin" ? "recycle_bin" : "task",
      title: payload.verb_noun || item.title || "Untitled task",
      description: payload.description || item.description || "",
      location: item.location || taskDetailLocation(payload),
      createdAt: payload.created_at || payload.createdAt || item.createdAt || "",
    };
  }

  if (payload.description && (item.kind === "waiting" || payload.person || payload.last_followup)) {
    return {
      ...item,
      ...payload,
      id: payload.id || item.id || "",
      kind: "waiting",
      title: payload.description || item.title || "Waiting On item",
      description: payload.person || item.description || "",
      location: item.location || "Waiting On",
      createdAt: payload.created_at || payload.createdAt || item.createdAt || "",
    };
  }

  return item;
}

function richItemDetailRows(item, payload) {
  if (!payload) return [];
  if (item.kind === "waiting") {
    return [
      { label: "Person", value: item.person },
      { label: "Project", value: item.project_id },
      { label: "Last follow-up", value: formatDetailDate(item.last_followup) },
    ];
  }

  if (item.kind === "project") {
    return [
      { label: "Status", value: titleCase(item.status) },
      { label: "Category", value: titleCase(item.category) },
      { label: "Start date", value: formatDetailDate(item.start_date) },
      { label: "Target date", value: formatDetailDate(item.target_date) },
      { label: "Success level", value: titleCase(item.level_of_success) },
      { label: "Active this week", value: booleanDetail(item.active_this_week) },
      { label: "Roadmap chunks", value: numberDetail(item.roadmapChunksCount) },
    ];
  }

  return [
    { label: "Status", value: titleCase(item.status) },
    { label: "Bucket", value: titleCase(item.when_bucket) },
    { label: "Block", value: titleCase(item.block_type) },
    { label: "Duration", value: minutesDetail(item.duration_minutes) },
    { label: "Frog", value: booleanDetail(item.frog) },
    { label: "Scheduled", value: formatDetailDate(item.scheduled_for) },
    { label: "Resurfaces", value: formatDetailDate(item.resurface_on) },
    { label: "Parked until", value: formatDetailDate(item.parked_until) },
    { label: "Completed", value: formatDetailDate(item.completed_at) },
  ];
}

function itemKindLabel(kind) {
  return (
    {
      project: "Project",
      task: "Task",
      waiting: "Waiting On",
      recycle_bin: "Recycled Task",
    }[kind] || titleCase(kind || "item")
  );
}

function workflowDisplayLabel(workflow) {
  return WORKFLOWS.find((item) => item.id === workflow)?.label || titleCase(workflow || "today");
}

function formatSearchTimestamp(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return formatDateTimeDisplayLabel(text);
}

function taskDetailLocation(task) {
  if (task.archived_from_inbox && task.status === "archived") return "Recycle Bin";
  if (task.in_inbox) return "Inbox";
  if (task.intake_container === "learn_explore") return "Learning";
  if (task.intake_container === "enjoy_recover") return "Enjoy";
  if (task.intake_container === "park_let_go" && task.parked_until) return "Parked until";
  if (task.intake_container === "park_let_go") return "Parked";
  if (task.status === "done") return "Completed Task";
  return "Task";
}

function formatDetailDate(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return formatDateDisplayLabel(text);
  }
  return formatDateTimeDisplayLabel(text);
}

function booleanDetail(value) {
  return value === true ? "Yes" : "";
}

function minutesDetail(value) {
  const minutes = Number(value || 0);
  return Number.isFinite(minutes) && minutes > 0 ? `${minutes} min` : "";
}

function numberDetail(value) {
  return Number.isFinite(value) ? String(value) : "";
}

function searchGroupLabel(kind) {
  return (
    {
      project: "Projects",
      task: "Tasks",
      waiting: "Waiting On",
      recycle_bin: "Recycle Bin",
    }[kind] || "Results"
  );
}

function searchResultWorkflow(kind, location) {
  if (kind === "project" || kind === "recycle_bin") return "review";
  if (kind === "waiting") return "today";
  if (["Inbox"].includes(location)) return "process";
  if (["Learning", "Enjoy", "Parked", "Parked until", "Completed Task"].includes(location)) {
    return "review";
  }
  return "today";
}

function reviewTaskView(task, actionLabel) {
  return {
    id: task.id || "",
    kind: "task",
    title: task.title || task.verb_noun || "Untitled task",
    description: task.description || "",
    meta: compactJoin([
      task.when_bucket,
      task.resurface_on ? `due ${task.resurface_on}` : "",
      task.completed_at ? `completed ${String(task.completed_at).slice(0, 10)}` : "",
    ]),
    location: actionLabel === "Archive" ? "Completed Task" : "Review",
    actionLabel,
  };
}

function routedInboxItemView(item, location = "Task") {
  const capturedLabel = item.created_at ? `Captured ${String(item.created_at).slice(0, 10)}` : "";
  const parkedUntilLabel = item.parked_until
    ? `Returns ${formatDateTimeDisplayLabel(item.parked_until)}`
    : "";

  return {
    id: item.id || "",
    kind: "task",
    title: item.verb_noun || item.title || "Untitled item",
    description: item.description || "",
    meta: compactJoin([parkedUntilLabel, capturedLabel]),
    location: item.parked_until ? "Parked until" : location,
    createdAt: item.created_at || item.createdAt || "",
    recycled: false,
    actionLabel: "Move to Inbox",
  };
}

function recycleBinItemView(item) {
  return {
    ...routedInboxItemView(item, "Recycle Bin"),
    kind: "recycle_bin",
    location: "Recycle Bin",
    recycled: true,
    actionLabel: "Restore",
  };
}

function countLabel(items) {
  return String(items.length);
}

function compactJoin(values, separator = " · ") {
  return values
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(separator);
}

function optionalText(value) {
  const text = String(value || "").trim();
  return text || null;
}

function displayItemTitle(value) {
  return optionalText(value) || "this item";
}

function displayTaskTitle(value) {
  return optionalText(value) || "this task";
}

function setOptional(target, key, value) {
  const text = optionalText(value);
  if (text) {
    target[key] = text;
  }
}

function checkboxValue(value) {
  return value === true || value === "true" || value === "on" || value === "1";
}

function positiveInteger(value) {
  const number = Number.parseInt(String(value || ""), 10);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function trimSeconds(value) {
  return String(value || "").replace(/^(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?$/, "$1");
}

function formatTodayDisplayLabel(todayLabel, currentTime) {
  const match = String(todayLabel || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return compactJoin([todayLabel, formatClockLabel(currentTime)], " ");
  }

  return compactJoin([formatDateDisplayLabel(todayLabel), formatClockLabel(currentTime)], " ");
}

function formatDateDisplayLabel(value) {
  const parts = dateDisplayParts(value);
  if (!parts) return String(value || "").trim();

  return `${parts.weekday} ${parts.day} ${parts.monthLabel} ${parts.year}`;
}

function formatWeekRangeDisplayLabel(value) {
  const start = dateDisplayParts(value);
  if (!start) return String(value || "").trim();

  const endDate = new Date(Date.UTC(start.year, start.month - 1, start.day + 6));
  const end = dateDisplayParts(endDate.toISOString().slice(0, 10));
  if (!end) return formatDateDisplayLabel(value);

  if (start.year !== end.year) {
    return `${start.weekday} ${start.day} ${start.monthLabel} ${start.year} - ${end.weekday} ${end.day} ${end.monthLabel} ${end.year}`;
  }

  return `${start.weekday} ${start.day} ${start.monthLabel} - ${end.weekday} ${end.day} ${end.monthLabel} ${end.year}`;
}

function formatDateTimeDisplayLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value || "").trim();

  const dateLabel = formatDateDisplayLabel(localDateKey(date));
  const timeLabel = formatClockLabel(localTimeKey(date));
  return compactJoin([dateLabel, timeLabel], " ");
}

function localDateKey(date) {
  return [
    date.getFullYear(),
    padDatePart(date.getMonth() + 1),
    padDatePart(date.getDate()),
  ].join("-");
}

function localTimeKey(date) {
  return [padDatePart(date.getHours()), padDatePart(date.getMinutes())].join(":");
}

function dateDisplayParts(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;

  const [, yearText, monthText, dayText] = match;
  const year = Number.parseInt(yearText, 10);
  const month = Number.parseInt(monthText, 10);
  const day = Number.parseInt(dayText, 10);
  const date = new Date(Date.UTC(year, month - 1, day));
  const weekday = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][date.getUTCDay()];
  const monthLabel = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ][month - 1];
  return { day, month, monthLabel, weekday, year };
}

function padDatePart(value) {
  return String(value).padStart(2, "0");
}

function formatClockLabel(value) {
  const match = String(value || "").match(/^(\d{2}):(\d{2})$/);
  if (!match) return String(value || "").trim();

  const [, hourText, minuteText] = match;
  const hour = Number.parseInt(hourText, 10);
  const suffix = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minuteText}${suffix}`;
}

function titleCase(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isLoopbackHost(host) {
  return host === "localhost" || host === "::1" || host.startsWith("127.");
}

function isPrivateNetworkHost(host) {
  const parts = host.split(".").map((part) => Number.parseInt(part, 10));
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part))) {
    return false;
  }
  const [first, second] = parts;
  return (
    first === 10 ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 168) ||
    (first === 169 && second === 254)
  );
}
