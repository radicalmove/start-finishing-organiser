import {
  WORKFLOWS,
  buildCaptureWorkflowViewModel,
  buildConnectionGuidance,
  buildGuidedCaptureFeedback,
  buildGuidedCapturePayload,
  buildGlobalSearchViewModel,
  buildItemDetailApiPath,
  buildItemDetailUpdatePayload,
  buildItemDetailViewModel,
  buildSearchApiPath,
  buildInboxActionFeedback,
  buildParkRoutePayload,
  buildProcessWorkflowViewModel,
  buildProjectCardPayload,
  buildProjectOptions,
  buildBootstrapViewModel,
  buildTodayTaskActionFeedback,
  buildWeeklyReviewActionFeedback,
  buildWeeklyReviewViewModel,
  clearSettings,
  defaultGuidedProjectTargetDate,
  getTauriNotification,
  getTauriInvoke,
  guidedDecisionCopy,
  guidedProcessStepPlan,
  inferGuidedProjectCategory,
  loadSettings,
  nextParkedItemRefreshDelay,
  requestJson,
  saveSettings,
  scheduleParkReminderNotifications,
} from "./client.js";

const INBOX_ROUTE_ACTIONS = {
  learn_explore: "Learning",
  enjoy_recover: "Enjoy",
  park_let_go: "Park",
};

const HORIZON_OPTIONS = [
  ["week", "This week"],
  ["today", "Today"],
  ["month", "This month"],
  ["quarter", "This quarter"],
  ["year", "This year"],
  ["later", "Later"],
];

const SUCCESS_LEVEL_OPTIONS = [
  ["", "Unspecified"],
  ["small", "Small - done and useful"],
  ["moderate", "Moderate - strong progress"],
  ["epic", "Epic - standout result"],
];

const PROJECT_STATUS_OPTIONS = [
  ["active", "Active"],
  ["paused", "Paused"],
  ["completed", "Completed"],
  ["archived", "Archived"],
];

const PROJECT_SIZE_OPTIONS = [
  ["", "Unspecified"],
  ["light", "Light"],
  ["moderate", "Moderate"],
  ["heavy", "Heavy"],
];

const DECISION_OPTIONS = [
  [
    "task",
    "Task",
    "A concrete next action that belongs inside an existing project.",
  ],
  [
    "project",
    "Project",
    "A multi-step outcome that deserves a target date and weekly attention.",
  ],
  [
    "opp",
    "Waiting On",
    "Something where another person owns the next move.",
  ],
];

const BLOCK_TYPE_OPTIONS = [
  ["", "No block type"],
  ["focus", "Focus"],
  ["admin", "Admin"],
  ["social", "Social"],
  ["recovery", "Recovery"],
];
const STARTUP_CONNECT_RETRY_MS = 1000;
const STARTUP_CONNECT_MAX_ATTEMPTS = 30;
const PARK_RESURFACE_MAX_TIMER_MS = 2147000000;
const PARK_CALENDAR_WEEKDAYS = [
  { label: "M", title: "Monday" },
  { label: "T", title: "Tuesday" },
  { label: "W", title: "Wednesday" },
  { label: "T", title: "Thursday" },
  { label: "F", title: "Friday" },
  { label: "S", title: "Saturday" },
  { label: "S", title: "Sunday" },
];

const elements = {
  statusDot: document.getElementById("status-dot"),
  status: document.getElementById("status"),
  detail: document.getElementById("detail"),
  connectionCard: document.getElementById("connection-card"),
  connectionForm: document.getElementById("connection-form"),
  serverUrl: document.getElementById("server-url"),
  apiToken: document.getElementById("api-token"),
  resetSettings: document.getElementById("reset-settings"),
  connectionReachability: document.getElementById("connection-reachability"),
  connectionReachabilityDetail: document.getElementById("connection-reachability-detail"),
  connectionTransport: document.getElementById("connection-transport"),
  connectionTransportDetail: document.getElementById("connection-transport-detail"),
  connectionAuth: document.getElementById("connection-auth"),
  connectionAuthDetail: document.getElementById("connection-auth-detail"),
  connectionStorage: document.getElementById("connection-storage"),
  dashboard: document.getElementById("dashboard"),
  workflowTabs: [...document.querySelectorAll("[data-workflow-tab]")],
  workflowPanels: [...document.querySelectorAll("[data-workflow-panel]")],
  actionFeedback: document.getElementById("action-feedback"),
  refreshDashboard: document.getElementById("refresh-dashboard"),
  globalSearchForm: document.getElementById("global-search-form"),
  globalSearchInput: document.getElementById("global-search-input"),
  globalSearchIncludeRecycle: document.getElementById("global-search-include-recycle"),
  globalSearchResults: document.getElementById("global-search-results"),
  itemDetailBackdrop: document.getElementById("item-detail-backdrop"),
  itemDetailDrawer: document.getElementById("item-detail-drawer"),
  itemDetailKind: document.getElementById("item-detail-kind"),
  itemDetailTitle: document.getElementById("item-detail-title"),
  itemDetailDescription: document.getElementById("item-detail-description"),
  itemDetailLoadState: document.getElementById("item-detail-load-state"),
  itemDetailEditForm: document.getElementById("item-detail-edit-form"),
  itemDetailEditFields: document.getElementById("item-detail-edit-fields"),
  itemDetailRows: document.getElementById("item-detail-rows"),
  itemDetailActions: document.getElementById("item-detail-actions"),
  itemDetailOpen: document.getElementById("item-detail-open"),
  todayLabel: document.getElementById("today-label"),
  captureTitle: document.getElementById("capture-title"),
  captureDescription: document.getElementById("capture-description"),
  quickCaptureForm: document.getElementById("quick-capture-form"),
  quickCaptureInput: document.getElementById("quick-capture-input"),
  dailyFocusForm: document.getElementById("daily-focus-form"),
  oneThingInput: document.getElementById("one-thing-input"),
  frogInput: document.getElementById("frog-input"),
  nowTitle: document.getElementById("now-title"),
  nowMeta: document.getElementById("now-meta"),
  nextBlock: document.getElementById("next-block"),
  inboxTotal: document.getElementById("inbox-total"),
  inboxCounts: document.getElementById("inbox-counts"),
  processWorkflow: document.getElementById("workflow-process"),
  processActiveItem: document.getElementById("process-active-item"),
  processActiveActions: document.getElementById("process-active-actions"),
  inboxItems: document.getElementById("inbox-items"),
  processPosition: document.getElementById("process-position"),
  ritualStatus: document.getElementById("ritual-status"),
  waitingSummary: document.getElementById("waiting-summary"),
  todayTasks: document.getElementById("today-tasks"),
  weeklyProjects: document.getElementById("weekly-projects"),
  todayBlocks: document.getElementById("today-blocks"),
  reviewDateLabel: document.getElementById("review-date-label"),
  reviewRefresh: document.getElementById("review-refresh"),
  reviewWorkCount: document.getElementById("review-work-count"),
  reviewPersonalCount: document.getElementById("review-personal-count"),
  reviewWeeklyProjects: document.getElementById("review-weekly-projects"),
  reviewWeeklyProjectsCount: document.getElementById("review-weekly-projects-count"),
  reviewFocusCandidates: document.getElementById("review-focus-candidates"),
  reviewFocusCandidatesCount: document.getElementById("review-focus-candidates-count"),
  reviewResurfaceDue: document.getElementById("review-resurface-due"),
  reviewResurfaceDueCount: document.getElementById("review-resurface-due-count"),
  reviewCompletedTasks: document.getElementById("review-completed-tasks"),
  reviewCompletedTasksCount: document.getElementById("review-completed-tasks-count"),
  reviewLearningItems: document.getElementById("review-learning-items"),
  reviewLearningCount: document.getElementById("review-learning-count"),
  reviewEnjoyItems: document.getElementById("review-enjoy-items"),
  reviewEnjoyCount: document.getElementById("review-enjoy-count"),
  reviewParkedItems: document.getElementById("review-parked-items"),
  reviewParkedCount: document.getElementById("review-parked-count"),
  reviewRecycleBinItems: document.getElementById("review-recycle-bin-items"),
  reviewRecycleBinCount: document.getElementById("review-recycle-bin-count"),
};

const tauriInvoke = getTauriInvoke(window);
const tauriNotification = getTauriNotification(window);
let settings = {
  serverUrl: elements.serverUrl.value,
  apiToken: "",
};
let lastAuthRequired = null;
let activeWorkflow = "today";
let startupReconnectTimer = null;
let startupReconnectAttempts = 0;
let parkResurfaceTimer = null;
let globalSearchTimer = null;
let itemDetailOpen = false;
let currentItemDetail = null;

function setWorkflow(workflow) {
  const nextWorkflow = WORKFLOWS.some((item) => item.id === workflow) ? workflow : "today";
  activeWorkflow = nextWorkflow;
  document.body.dataset.workflow = nextWorkflow;
  elements.dashboard.classList.remove("hidden");

  for (const tab of elements.workflowTabs) {
    const selected = tab.dataset.workflowTab === nextWorkflow;
    tab.classList.toggle("is-active", selected);
    tab.setAttribute("aria-selected", String(selected));
  }

  for (const panel of elements.workflowPanels) {
    panel.classList.toggle("hidden", panel.dataset.workflowPanel !== nextWorkflow);
  }
}

function setConnectionState(state, message, detail = "") {
  document.body.dataset.connectionState = state;
  elements.statusDot.dataset.state = state;
  elements.status.textContent = message;
  elements.detail.textContent = detail;
}

function applySettingsToForm() {
  elements.serverUrl.value = settings.serverUrl;
  elements.apiToken.value = settings.apiToken;
  renderConnectionGuidance();
}

function renderConnectionGuidance(authRequired = lastAuthRequired) {
  try {
    const guidance = buildConnectionGuidance(elements.serverUrl.value || settings.serverUrl, {
      authRequired,
      apiToken: elements.apiToken.value,
      nativeCredentialStorage: Boolean(tauriInvoke),
    });
    setGuidance(
      elements.connectionReachability,
      elements.connectionReachabilityDetail,
      guidance.reachabilityLabel,
      guidance.reachabilityDetail,
    );
    setGuidance(
      elements.connectionTransport,
      elements.connectionTransportDetail,
      guidance.transportLabel,
      guidance.transportDetail,
    );
    setGuidance(
      elements.connectionAuth,
      elements.connectionAuthDetail,
      guidance.authLabel,
      guidance.authDetail,
    );
    elements.connectionStorage.textContent = guidance.storageDetail;
  } catch (err) {
    setGuidance(
      elements.connectionReachability,
      elements.connectionReachabilityDetail,
      "Invalid URL",
      err instanceof Error ? err.message : String(err),
    );
    setGuidance(
      elements.connectionTransport,
      elements.connectionTransportDetail,
      "Unknown",
      "Enter a valid http or https URL to check the connection shape.",
    );
    setGuidance(
      elements.connectionAuth,
      elements.connectionAuthDetail,
      "Auth unknown",
      "Connect to the server to confirm whether an API token is required.",
    );
  }
}

function setGuidance(labelElement, detailElement, label, detail) {
  labelElement.textContent = label;
  detailElement.textContent = detail;
}

function scheduleGlobalSearch() {
  if (globalSearchTimer) {
    window.clearTimeout(globalSearchTimer);
  }
  globalSearchTimer = window.setTimeout(() => {
    globalSearchTimer = null;
    performGlobalSearch();
  }, 220);
}

async function performGlobalSearch() {
  const path = buildSearchApiPath(
    elements.globalSearchInput.value,
    elements.globalSearchIncludeRecycle.checked,
  );
  if (!path) {
    hideGlobalSearchResults();
    return;
  }

  renderGlobalSearchResults(
    buildGlobalSearchViewModel({
      query: elements.globalSearchInput.value.trim(),
      include_recycle_bin: elements.globalSearchIncludeRecycle.checked,
      items: [],
    }),
    true,
  );

  try {
    const payload = await requestJson(window.fetch.bind(window), settings, path);
    renderGlobalSearchResults(buildGlobalSearchViewModel(payload));
  } catch (err) {
    elements.globalSearchResults.replaceChildren(emptyState(`Search failed: ${err.message}`));
    elements.globalSearchResults.classList.remove("hidden");
  }
}

function renderGlobalSearchResults(model, loading = false) {
  elements.globalSearchResults.replaceChildren();
  if (!model.hasQuery) {
    hideGlobalSearchResults();
    return;
  }

  const heading = document.createElement("div");
  heading.className = "search-results-heading";
  const label = document.createElement("span");
  label.textContent = loading ? "Searching..." : model.totalCountLabel;
  const scope = document.createElement("span");
  scope.textContent = model.includeRecycleBin ? "Recycle included" : "Active items";
  heading.append(label, scope);
  elements.globalSearchResults.append(heading);

  if (!loading && !model.groups.length) {
    elements.globalSearchResults.append(emptyState(model.emptyText));
  }

  for (const group of model.groups) {
    const section = document.createElement("section");
    section.className = "search-results-group";
    const title = document.createElement("h4");
    title.textContent = group.label;
    section.append(title);
    for (const item of group.items) {
      section.append(searchResultButton(item));
    }
    elements.globalSearchResults.append(section);
  }

  elements.globalSearchResults.classList.remove("hidden");
}

function searchResultButton(item) {
  const button = document.createElement("button");
  button.className = "search-result-row";
  button.type = "button";
  button.dataset.searchResultWorkflow = item.workflow;
  button.dataset.searchResultId = item.id;
  button.dataset.searchResultKind = item.kind;
  button.dataset.searchResultTitle = item.title;
  button.dataset.searchResultDescription = item.description || "";
  button.dataset.searchResultLocation = item.location || "";
  button.dataset.searchResultRecycled = String(Boolean(item.recycled));
  button.dataset.searchResultCreatedAt = item.createdAt || "";
  button.classList.toggle("is-recycled", item.recycled);

  const title = document.createElement("span");
  title.className = "search-result-title";
  title.textContent = item.title;
  const meta = document.createElement("span");
  meta.className = "search-result-meta";
  meta.textContent = item.badge;
  button.append(title, meta);
  if (item.description) {
    const description = document.createElement("span");
    description.className = "search-result-description";
    description.textContent = item.description;
    button.append(description);
  }
  return button;
}

function hideGlobalSearchResults() {
  elements.globalSearchResults.replaceChildren();
  elements.globalSearchResults.classList.add("hidden");
}

function openItemDetail(item) {
  const detail = buildItemDetailViewModel(item);
  currentItemDetail = detail;
  itemDetailOpen = true;
  document.body.dataset.itemDetailOpen = "true";
  renderItemDetail(detail);
  elements.itemDetailBackdrop.classList.remove("hidden");
  elements.itemDetailDrawer.classList.remove("hidden");
  elements.itemDetailDrawer.setAttribute("aria-hidden", "false");
  loadItemDetail(detail);
}

function closeItemDetail() {
  itemDetailOpen = false;
  currentItemDetail = null;
  delete document.body.dataset.itemDetailOpen;
  elements.itemDetailLoadState.textContent = "";
  elements.itemDetailBackdrop.classList.add("hidden");
  elements.itemDetailDrawer.classList.add("hidden");
  elements.itemDetailDrawer.setAttribute("aria-hidden", "true");
}

function renderItemDetail(detail) {
  elements.itemDetailKind.textContent = detail.kindLabel;
  elements.itemDetailTitle.textContent = detail.title;
  elements.itemDetailDescription.textContent = detail.description || "No notes yet.";
  elements.itemDetailDescription.classList.toggle("is-empty", !detail.description);
  elements.itemDetailRows.replaceChildren();
  elements.itemDetailActions.replaceChildren();
  renderItemDetailEditForm(detail.edit);

  for (const row of detail.rows) {
    const item = document.createElement("div");
    const label = document.createElement("span");
    label.textContent = row.label;
    const value = document.createElement("strong");
    value.textContent = row.value;
    item.append(label, value);
    elements.itemDetailRows.append(item);
  }

  for (const action of detail.actions || []) {
    const button = document.createElement("button");
    button.className = action.primary ? "primary-button" : "mini-button quiet";
    button.type = "button";
    button.dataset.itemDetailActionId = action.id;
    button.dataset.workflowTarget = action.workflow || "";
    button.dataset.actionPath = action.path || "";
    button.dataset.actionMethod = action.method || "POST";
    button.dataset.projectId = action.projectId || "";
    button.textContent = action.label;
    elements.itemDetailActions.append(button);
  }
}

function renderItemDetailEditForm(edit) {
  elements.itemDetailEditFields.replaceChildren();
  elements.itemDetailEditForm.hidden = !edit;
  elements.itemDetailEditForm.dataset.editPath = edit?.path || "";
  elements.itemDetailEditForm.dataset.editMethod = edit?.method || "PATCH";

  if (!edit) return;

  for (const field of edit.fields || []) {
    const label = document.createElement("label");
    label.className = "item-detail-edit-field";
    const text = document.createElement("span");
    text.textContent = field.label;
    const input =
      field.type === "textarea" ? document.createElement("textarea") : document.createElement("input");
    input.name = field.name;
    input.value = field.value || "";
    input.placeholder = field.placeholder || "";
    input.required = Boolean(field.required);
    if (field.type !== "textarea") {
      input.type = field.type || "text";
    } else {
      input.rows = 3;
    }
    label.append(text, input);
    elements.itemDetailEditFields.append(label);
  }

  const submit = document.createElement("button");
  submit.className = "ghost-button";
  submit.type = "submit";
  submit.textContent = edit.submitLabel || "Save";
  elements.itemDetailEditFields.append(submit);
}

async function loadItemDetail(detail) {
  const path = buildItemDetailApiPath(detail);
  if (!path) {
    elements.itemDetailLoadState.textContent = "";
    return;
  }

  elements.itemDetailLoadState.textContent = "Loading full details...";
  try {
    const payload = await requestJson(window.fetch.bind(window), settings, path);
    if (!itemDetailOpen || currentItemDetail?.id !== detail.id) return;

    const enrichedDetail = buildItemDetailViewModel(detail, payload);
    currentItemDetail = enrichedDetail;
    renderItemDetail(enrichedDetail);
    elements.itemDetailLoadState.textContent = "Full details loaded.";
  } catch (err) {
    if (!itemDetailOpen || currentItemDetail?.id !== detail.id) return;
    elements.itemDetailLoadState.textContent = `Could not load full details: ${
      err instanceof Error ? err.message : String(err)
    }`;
  }
}

async function saveItemDetailEdit(event) {
  event.preventDefault();
  const detail = currentItemDetail;
  const edit = detail?.edit;
  if (!detail || !edit) return;

  const submitButton = elements.itemDetailEditForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  try {
    const values = Object.fromEntries(new FormData(elements.itemDetailEditForm).entries());
    const payload = buildItemDetailUpdatePayload(edit, values);
    elements.itemDetailLoadState.textContent = "Saving changes...";
    const updated = await requestJson(window.fetch.bind(window), settings, edit.path, {
      method: edit.method || "PATCH",
      body: payload,
    });
    if (!itemDetailOpen || currentItemDetail?.id !== detail.id) return;

    const enrichedDetail = buildItemDetailViewModel(detail, updated);
    currentItemDetail = enrichedDetail;
    renderItemDetail(enrichedDetail);
    elements.itemDetailLoadState.textContent = "Saved.";
    await refreshWorkflowData(activeWorkflow);
  } catch (err) {
    elements.itemDetailLoadState.textContent = err instanceof Error ? err.message : String(err);
  } finally {
    submitButton.disabled = false;
  }
}

async function performItemDetailAction(button) {
  const actionId = button.dataset.itemDetailActionId || "";
  const detail = currentItemDetail;
  if (!detail) return;

  if (actionId === "open-workflow") {
    closeItemDetail();
    await openItemDetailWorkflow(button.dataset.workflowTarget || detail.workflow || "today");
    return;
  }

  if (actionId === "open-shape-card") {
    closeItemDetail();
    await openProjectShapeCard(button.dataset.projectId || detail.id);
    return;
  }

  const path = button.dataset.actionPath || "";
  if (!path) return;

  button.disabled = true;
  try {
    await requestJson(window.fetch.bind(window), settings, path, {
      method: button.dataset.actionMethod || "POST",
    });
    closeItemDetail();
    await refreshWorkflowData(activeWorkflow);
    showActionFeedback(itemDetailActionFeedback(actionId, detail.title));
  } catch (err) {
    setConnectionState(
      "error",
      "Item detail action failed",
      err instanceof Error ? err.message : String(err),
    );
  } finally {
    button.disabled = false;
  }
}

async function openItemDetailWorkflow(workflow) {
  setWorkflow(workflow);
  await refreshWorkflowData(workflow);
}

async function openProjectShapeCard(projectId) {
  await openItemDetailWorkflow("review");
  const shapeButton = [...document.querySelectorAll("[data-review-action='toggle-project-card']")]
    .find((button) => button.dataset.projectId === projectId);

  if (!shapeButton) {
    showActionFeedback({
      message: "Opened Review. This project is not currently visible in the review lists.",
    });
    return;
  }

  shapeButton.click();
  shapeButton.scrollIntoView({ block: "center", behavior: "smooth" });
}

function itemDetailActionFeedback(actionId, title) {
  const itemTitle = title || "this item";
  const messages = {
    "complete-task": `Completed "${itemTitle}".`,
    "reopen-task": `Reopened "${itemTitle}".`,
    "restore-task": `Restored "${itemTitle}".`,
    "resolve-waiting": `Resolved "${itemTitle}".`,
  };
  return { message: messages[actionId] || `Updated "${itemTitle}".` };
}

function searchResultDetail(button) {
  return {
    id: button.dataset.searchResultId || "",
    kind: button.dataset.searchResultKind || "task",
    title: button.dataset.searchResultTitle || "",
    description: button.dataset.searchResultDescription || "",
    location: button.dataset.searchResultLocation || "",
    recycled: button.dataset.searchResultRecycled === "true",
    createdAt: button.dataset.searchResultCreatedAt || "",
  };
}

function attachItemDetail(element, item = {}) {
  element.classList.add("has-item-detail");
  element.dataset.itemDetail = "true";
  element.dataset.itemDetailId = item.id || "";
  element.dataset.itemDetailKind = item.kind || "task";
  element.dataset.itemDetailTitle = item.title || "Untitled item";
  element.dataset.itemDetailDescription = item.description || "";
  element.dataset.itemDetailLocation = item.location || "";
  element.dataset.itemDetailRecycled = String(Boolean(item.recycled));
  element.dataset.itemDetailCreatedAt = item.createdAt || item.created_at || "";
  element.tabIndex = 0;
  element.setAttribute("role", "button");
  element.setAttribute("aria-label", `Open ${item.title || "item"} details`);
  return element;
}

function itemDetailFromElement(element) {
  return {
    id: element.dataset.itemDetailId || "",
    kind: element.dataset.itemDetailKind || "task",
    title: element.dataset.itemDetailTitle || "",
    description: element.dataset.itemDetailDescription || "",
    location: element.dataset.itemDetailLocation || "",
    recycled: element.dataset.itemDetailRecycled === "true",
    createdAt: element.dataset.itemDetailCreatedAt || "",
  };
}

function isItemDetailInteractiveTarget(target) {
  return Boolean(
    target.closest("button, input, select, textarea, summary, form, a, [data-item-detail-close]"),
  );
}

async function connectAndLoad(options = {}) {
  clearActionFeedback();
  await saveSettings(window.localStorage, settings, tauriInvoke);
  lastAuthRequired = null;
  applySettingsToForm();
  setConnectionState("loading", "Checking Rust server...", settings.serverUrl);

  try {
    const health = await requestJson(window.fetch.bind(window), settings, "/healthz");
    if (health?.status !== "ok") {
      throw new Error(health?.detail || "Server health check did not report ok");
    }

    const auth = await requestJson(window.fetch.bind(window), settings, "/api/v1/auth/status");
    lastAuthRequired = Boolean(auth?.auth_required);
    renderConnectionGuidance(lastAuthRequired);
    if (auth?.auth_required && !settings.apiToken) {
      throw new Error("This server requires an API token.");
    }

    const [summary, inboxContainers, projectsPage, weeklyReview] = await Promise.all([
      requestJson(window.fetch.bind(window), settings, "/api/v1/bootstrap"),
      requestJson(window.fetch.bind(window), settings, "/api/v1/inbox/containers"),
      requestJson(window.fetch.bind(window), settings, "/api/v1/projects?page=1&page_size=100"),
      requestJson(window.fetch.bind(window), settings, "/api/v1/weekly-review"),
    ]);
    const dashboardModel = buildBootstrapViewModel(summary);
    renderDashboard(dashboardModel);
    renderProcessWorkflow(
      buildProcessWorkflowViewModel(inboxContainers),
      buildProjectOptions(projectsPage),
      defaultGuidedProjectTargetDate(dashboardModel.todayLabel),
    );
    renderWeeklyReview(buildWeeklyReviewViewModel(weeklyReview, inboxContainers));
    await syncNativeParkReminders(inboxContainers);
    if (startupReconnectTimer) {
      window.clearTimeout(startupReconnectTimer);
      startupReconnectTimer = null;
    }
    startupReconnectAttempts = 0;
    setConnectionState(
      "ready",
      auth?.auth_required ? "Connected with API token" : "Connected without auth",
      `${settings.serverUrl} · database ${summary?.system?.database_status || "unknown"}`,
    );
  } catch (err) {
    if (options.startupRetry === true) {
      scheduleStartupReconnect();
      setConnectionState(
        "loading",
        "Starting local server...",
        err instanceof Error ? err.message : String(err),
      );
      return;
    }
    setConnectionState(
      "error",
      "Connection needs attention",
      err instanceof Error ? err.message : String(err),
    );
    if (options.startupRetry !== true) {
      setWorkflow("settings");
    }
  }
}

function scheduleStartupReconnect() {
  if (startupReconnectTimer) return;
  if (startupReconnectAttempts >= STARTUP_CONNECT_MAX_ATTEMPTS) {
    setConnectionState(
      "error",
      "Connection needs attention",
      "The local server did not become ready. Check Settings or restart the app.",
    );
    setWorkflow("settings");
    return;
  }

  startupReconnectAttempts += 1;
  setConnectionState(
    "loading",
    "Starting local server...",
    `Waiting for ${settings.serverUrl} (${startupReconnectAttempts}/${STARTUP_CONNECT_MAX_ATTEMPTS})`,
  );

  startupReconnectTimer = window.setTimeout(() => {
    startupReconnectTimer = null;
    connectAndLoad({ startupRetry: true }).catch((err) => {
      setConnectionState(
        "error",
        "Connection needs attention",
        err instanceof Error ? err.message : String(err),
      );
      setWorkflow("settings");
    });
  }, STARTUP_CONNECT_RETRY_MS);
}

async function refreshDashboardAndReview() {
  const [summary, weeklyReview, inboxContainers] = await Promise.all([
    requestJson(window.fetch.bind(window), settings, "/api/v1/bootstrap"),
    requestJson(window.fetch.bind(window), settings, "/api/v1/weekly-review"),
    requestJson(window.fetch.bind(window), settings, "/api/v1/inbox/containers"),
  ]);
  renderDashboard(buildBootstrapViewModel(summary));
  renderWeeklyReview(buildWeeklyReviewViewModel(weeklyReview, inboxContainers));
  await syncNativeParkReminders(inboxContainers);
}

async function refreshDashboardAndProcess() {
  const [summary, inboxContainers, projectsPage] = await Promise.all([
    requestJson(window.fetch.bind(window), settings, "/api/v1/bootstrap"),
    requestJson(window.fetch.bind(window), settings, "/api/v1/inbox/containers"),
    requestJson(window.fetch.bind(window), settings, "/api/v1/projects?page=1&page_size=100"),
  ]);
  const dashboardModel = buildBootstrapViewModel(summary);
  renderDashboard(dashboardModel);
  renderProcessWorkflow(
    buildProcessWorkflowViewModel(inboxContainers),
    buildProjectOptions(projectsPage),
    defaultGuidedProjectTargetDate(dashboardModel.todayLabel),
  );
  await syncNativeParkReminders(inboxContainers);
}

async function refreshWorkflowData(workflow) {
  if (["today", "capture", "process"].includes(workflow)) {
    await refreshDashboardAndProcess();
    return;
  }

  if (workflow === "review") {
    await refreshDashboardAndReview();
  }
}

async function reloadWeeklyReview() {
  const [weeklyReview, inboxContainers] = await Promise.all([
    requestJson(window.fetch.bind(window), settings, "/api/v1/weekly-review"),
    requestJson(window.fetch.bind(window), settings, "/api/v1/inbox/containers"),
  ]);
  renderWeeklyReview(buildWeeklyReviewViewModel(weeklyReview, inboxContainers));
  await syncNativeParkReminders(inboxContainers);
}

async function syncNativeParkReminders(inboxContainers) {
  scheduleParkResurfaceRefresh(inboxContainers);
  try {
    await scheduleParkReminderNotifications(tauriNotification, inboxContainers);
  } catch (err) {
    console.warn("SFO park reminder scheduling failed", err);
  }
}

function scheduleParkResurfaceRefresh(inboxContainers) {
  if (parkResurfaceTimer) {
    window.clearTimeout(parkResurfaceTimer);
    parkResurfaceTimer = null;
  }

  const delay = nextParkedItemRefreshDelay(inboxContainers);
  if (delay === null) return;

  parkResurfaceTimer = window.setTimeout(async () => {
    parkResurfaceTimer = null;
    try {
      await refreshWorkflowData(activeWorkflow);
    } catch (err) {
      setConnectionState(
        "error",
        "Parked item refresh failed",
        err instanceof Error ? err.message : String(err),
      );
    }
  }, Math.min(delay, PARK_RESURFACE_MAX_TIMER_MS));
}

function renderDashboard(model) {
  elements.dashboard.classList.remove("hidden");
  elements.todayLabel.textContent = model.todayDisplayLabel || model.todayLabel;
  elements.nowTitle.textContent = model.now.title;
  elements.nowMeta.textContent = [model.now.time, model.now.meta].filter(Boolean).join(" · ");
  if (model.next) {
    elements.nextBlock.classList.remove("hidden");
    elements.nextBlock.textContent = `Next: ${model.next.time} · ${model.next.title}`;
  } else {
    elements.nextBlock.classList.add("hidden");
    elements.nextBlock.textContent = "";
  }

  elements.inboxTotal.textContent = String(model.inboxTotal);
  elements.inboxCounts.replaceChildren();
  elements.oneThingInput.value = model.dailyFocus.oneThing;
  elements.frogInput.value = model.dailyFocus.frog;
  elements.ritualStatus.textContent = ritualStatusText(model.rituals);
  elements.waitingSummary.textContent = model.waiting.label;
  renderTodayTasks(elements.todayTasks, model.todayTasks);
  renderItems(elements.weeklyProjects, model.weeklyProjects, "No weekly projects selected.");
  renderBlocks(elements.todayBlocks, model.todayBlocks);
}

function renderCaptureWorkflow() {
  const model = buildCaptureWorkflowViewModel();
  elements.captureTitle.textContent = model.title;
  elements.captureDescription.textContent = model.description;
  elements.quickCaptureInput.placeholder = model.placeholder;
  elements.quickCaptureForm.querySelector('button[type="submit"]').textContent =
    model.primaryAction;
}

function renderProcessWorkflow(model, projectOptions = [], projectTargetDate = "") {
  elements.processPosition.textContent = model.positionLabel;
  elements.processActiveItem.replaceChildren();
  elements.processActiveActions.replaceChildren();
  elements.inboxItems.replaceChildren();
  if (!model.queue.length) {
    elements.processActiveItem.append(
      emptyState("Inbox is clear. Capture something when it appears."),
    );
    elements.inboxItems.append(emptyState("Inbox is clear. Capture something when it appears."));
    return;
  }

  const item = model.activeItem || model.queue[0];
  if (!item) return;

  const activeCard = document.createElement("div");
  activeCard.className = "inbox-item process-primary process-active-card";
  activeCard.append(inboxItemBody(item));
  elements.processActiveItem.append(activeCard);
  elements.processActiveActions.append(...buildInboxActions(item));

  elements.inboxItems.append(parkChoicePanel(item));
  const details = guidedCaptureDetails(item, projectOptions, projectTargetDate);
  details.open = true;
  elements.inboxItems.append(details);
}

function renderWeeklyReview(model) {
  elements.reviewDateLabel.textContent = model.reviewLabel;
  elements.reviewWorkCount.textContent = model.focusCounts.work.label;
  elements.reviewPersonalCount.textContent = model.focusCounts.personal.label;
  elements.reviewWorkCount
    .closest(".review-count-card")
    ?.classList.toggle("at-cap", model.focusCounts.work.atCap);
  elements.reviewPersonalCount
    .closest(".review-count-card")
    ?.classList.toggle("at-cap", model.focusCounts.personal.atCap);
  elements.reviewWeeklyProjectsCount.textContent = model.weeklyProjectsCountLabel;
  elements.reviewFocusCandidatesCount.textContent = model.focusCandidatesCountLabel;
  elements.reviewResurfaceDueCount.textContent = model.resurfaceDueCountLabel;
  elements.reviewCompletedTasksCount.textContent = model.completedTasksCountLabel;
  elements.reviewLearningCount.textContent = model.learningItemsCountLabel;
  elements.reviewEnjoyCount.textContent = model.enjoyItemsCountLabel;
  elements.reviewParkedCount.textContent = model.parkedItemsCountLabel;
  elements.reviewRecycleBinCount.textContent = model.recycleBinItemsCountLabel;

  renderReviewProjects(
    elements.reviewWeeklyProjects,
    model.weeklyProjects,
    model.emptyWeeklyProjects,
  );
  renderReviewFocusCandidates(
    elements.reviewFocusCandidates,
    model.focusCandidates,
    model.emptyFocusCandidates,
  );
  renderReviewTasks(
    elements.reviewResurfaceDue,
    model.resurfaceDue,
    model.emptyResurfaceDue,
    "move-to-week",
  );
  renderReviewTasks(
    elements.reviewCompletedTasks,
    model.completedTasks,
    model.emptyCompletedTasks,
    "archive-task",
  );
  renderRoutedInboxItems(
    elements.reviewLearningItems,
    model.learningItems,
    model.emptyLearningItems,
  );
  renderRoutedInboxItems(elements.reviewEnjoyItems, model.enjoyItems, model.emptyEnjoyItems);
  renderRoutedInboxItems(elements.reviewParkedItems, model.parkedItems, model.emptyParkedItems);
  renderRecycleBinItems(
    elements.reviewRecycleBinItems,
    model.recycleBinItems,
    model.emptyRecycleBinItems,
  );
}

function renderReviewProjects(container, projects, emptyText) {
  container.replaceChildren();
  if (!projects.length) {
    container.append(emptyState(emptyText));
    return;
  }

  for (const project of projects) {
    container.append(reviewProjectCard(project));
  }
}

function renderReviewFocusCandidates(container, projects, emptyText) {
  container.replaceChildren();
  if (!projects.length) {
    container.append(emptyState(emptyText));
    return;
  }

  for (const project of projects) {
    container.append(reviewProjectCard(project, "focus-toggle"));
  }
}

function renderReviewTasks(container, tasks, emptyText, action) {
  container.replaceChildren();
  if (!tasks.length) {
    container.append(emptyState(emptyText));
    return;
  }

  for (const task of tasks) {
    container.append(reviewTaskRow(task, action));
  }
}

function renderRoutedInboxItems(container, items, emptyText) {
  container.replaceChildren();
  if (!items.length) {
    container.append(emptyState(emptyText));
    return;
  }

  for (const item of items) {
    container.append(reviewInboxItemRow(item));
  }
}

function renderRecycleBinItems(container, items, emptyText) {
  container.replaceChildren();
  if (!items.length) {
    container.append(emptyState(emptyText));
    return;
  }

  for (const item of items) {
    container.append(reviewRecycleBinItemRow(item));
  }
}

function reviewProjectCard(project, action = "") {
  const card = document.createElement("div");
  card.className = "review-card";
  card.classList.toggle("is-active", Boolean(project.active));

  const body = document.createElement("div");
  body.className = "review-card-body";
  const title = document.createElement("strong");
  title.textContent = project.title;
  const meta = document.createElement("span");
  meta.textContent = project.meta || project.category || "";
  body.append(title, meta);
  if (project.description) {
    const description = document.createElement("small");
    description.textContent = project.description;
    body.append(description);
  }
  attachItemDetail(body, project);
  card.append(body);

  const actions = document.createElement("div");
  actions.className = "review-card-actions";
  if (project.id) {
    const shapeButton = document.createElement("button");
    shapeButton.className = "mini-button quiet";
    shapeButton.type = "button";
    shapeButton.dataset.reviewAction = "toggle-project-card";
    shapeButton.dataset.projectId = project.id;
    shapeButton.dataset.projectTitle = project.title;
    shapeButton.textContent = "Shape";
    actions.append(shapeButton);
  }

  if (action) {
    const button = document.createElement("button");
    button.className = project.active ? "mini-button quiet" : "mini-button";
    button.type = "button";
    button.dataset.reviewAction = action;
    button.dataset.projectId = project.id;
    button.dataset.projectTitle = project.title;
    button.dataset.nextActive = String(project.nextActive);
    button.disabled = !project.id;
    button.textContent = project.toggleLabel;
    actions.append(button);
  }
  if (actions.childElementCount) {
    card.append(actions);
  }

  const details = document.createElement("div");
  details.className = "project-card-detail hidden";
  details.dataset.projectCardDetail = project.id || "";
  card.append(details);

  return card;
}

function renderProjectCardDetail(container, card) {
  const project = card?.project || {};
  const successPack = card?.success_pack || {};
  const chunks = card?.chunks || [];
  container.replaceChildren(projectCardForm(project, successPack), projectChunkPanel(project, chunks));
  container.dataset.loaded = "true";
}

function projectCardForm(project, successPack) {
  const form = document.createElement("form");
  form.className = "project-card-form";
  form.dataset.projectId = project.id || "";

  form.append(
    projectCardSection("Finish line", [
      formField("Title", textInput("title", project.title, "Verb-noun project title")),
      formField("Status", selectInput("status", PROJECT_STATUS_OPTIONS, project.status || "active")),
      formField("Category", selectInput("category", [["work", "Work"], ["personal", "Personal"]], project.category || "work")),
      formField("Size", selectInput("size", PROJECT_SIZE_OPTIONS, project.size || "")),
      formField("Horizon", selectInput("time_horizon", [["", "Unspecified"], ["week", "Week"], ["month", "Month"], ["quarter", "Quarter"], ["year", "Year"], ["later", "Later"]], project.time_horizon || "")),
      formField("Start date", textInput("start_date", project.start_date, "Optional", "date")),
      formField("Target date", requiredTextInput("target_date", project.target_date, "Required", "date")),
      formField("Success level", selectInput("level_of_success", SUCCESS_LEVEL_OPTIONS, project.level_of_success || "")),
      checkboxField("Active this week", "active_this_week", Boolean(project.active_this_week)),
      checkboxField("Allow non-action title", "verb_check_ack", false),
    ]),
    projectCardSection("Why and constraints", [
      formField("Why", textAreaInput("why_link_text", project.why_link_text, "Why does this matter?"), "full"),
      formField("Description", textAreaInput("description", project.description, "Useful scope notes"), "full"),
      formField("GATES", textAreaInput("gates_notes", project.gates_notes, "Genius, affinity, talents, expertise, strengths"), "full"),
      formField("Drag points", textAreaInput("drag_points_notes", project.drag_points_notes, "Likely friction, derailers, or OPP"), "full"),
      formField("Budget / space", textAreaInput("budget_notes", project.budget_notes, "Focus blocks, money, energy, or support needed"), "full"),
    ]),
    projectCardSection("Success pack", [
      formField("Guides", textAreaInput("success_pack_guides", successPack.guides, "People or sources that can guide this"), "full"),
      formField("Peers", textAreaInput("success_pack_peers", successPack.peers, "People working beside you"), "full"),
      formField("Supporters", textAreaInput("success_pack_supporters", successPack.supporters, "People who can make space"), "full"),
      formField("Beneficiaries", textAreaInput("success_pack_beneficiaries", successPack.beneficiaries, "Who benefits when this is finished?"), "full"),
    ]),
  );

  const actions = document.createElement("div");
  actions.className = "project-card-actions";
  const save = document.createElement("button");
  save.className = "mini-button";
  save.type = "submit";
  save.textContent = "Save project card";
  actions.append(save);
  form.append(actions);
  return form;
}

function projectCardSection(titleText, fields) {
  const section = document.createElement("details");
  section.className = "project-card-section";
  section.open = true;
  const summary = document.createElement("summary");
  summary.textContent = titleText;
  const grid = document.createElement("div");
  grid.className = "project-card-grid";
  grid.append(...fields);
  section.append(summary, grid);
  return section;
}

function projectChunkPanel(project, chunks) {
  const panel = document.createElement("section");
  panel.className = "project-chunk-panel";
  const heading = document.createElement("h4");
  heading.textContent = "Roadmap chunks";
  const list = document.createElement("div");
  list.className = "project-chunk-list";
  if (!chunks.length) {
    list.append(emptyState("No chunks yet. Add the next small piece."));
  } else {
    for (const chunk of chunks) {
      const item = document.createElement("div");
      item.className = "project-chunk-item";
      const title = document.createElement("strong");
      title.textContent = chunk.verb_noun || "Untitled chunk";
      const meta = document.createElement("span");
      meta.textContent = [chunk.when_bucket, chunk.duration_minutes ? `${chunk.duration_minutes} min` : ""]
        .filter(Boolean)
        .join(" · ");
      item.append(title, meta);
      list.append(item);
    }
  }

  const form = document.createElement("form");
  form.className = "project-chunk-form";
  form.dataset.projectId = project.id || "";
  form.append(
    formField("Next chunk", requiredTextInput("verb_noun", "", "Draft next small chunk")),
    formField("Minutes", textInput("duration_minutes", "", "Optional", "number")),
  );
  const button = document.createElement("button");
  button.className = "mini-button";
  button.type = "submit";
  button.textContent = "Add chunk";
  form.append(button);

  panel.append(heading, list, form);
  return panel;
}

function reviewTaskRow(task, action) {
  const row = document.createElement("div");
  row.className = "review-task-row";
  attachItemDetail(row, task);

  const body = document.createElement("div");
  body.className = "review-task-body";
  const title = document.createElement("strong");
  title.textContent = task.title;
  const meta = document.createElement("span");
  meta.textContent = task.meta || task.description || "";
  body.append(title, meta);
  if (task.description && task.meta) {
    const description = document.createElement("span");
    description.textContent = task.description;
    body.append(description);
  }

  const actions = document.createElement("div");
  actions.className = "review-task-actions";
  const button = document.createElement("button");
  button.className = action === "archive-task" ? "mini-button quiet" : "mini-button";
  button.type = "button";
  button.dataset.reviewAction = action;
  button.dataset.taskId = task.id;
  button.dataset.taskTitle = task.title;
  button.disabled = !task.id;
  button.textContent = task.actionLabel;
  actions.append(button);

  row.append(body, actions);
  return row;
}

function reviewInboxItemRow(item) {
  const row = document.createElement("div");
  row.className = "review-task-row";
  attachItemDetail(row, item);

  const body = document.createElement("div");
  body.className = "review-task-body";
  const title = document.createElement("strong");
  title.textContent = item.title;
  const meta = document.createElement("span");
  meta.textContent = item.meta || item.description || "";
  body.append(title, meta);
  if (item.description && item.meta) {
    const description = document.createElement("span");
    description.textContent = item.description;
    body.append(description);
  }

  const actions = document.createElement("div");
  actions.className = "review-task-actions";
  const restoreButton = document.createElement("button");
  restoreButton.className = "mini-button";
  restoreButton.type = "button";
  restoreButton.dataset.reviewInboxAction = "restore-inbox-item";
  restoreButton.dataset.itemId = item.id;
  restoreButton.dataset.itemTitle = item.title;
  restoreButton.disabled = !item.id;
  restoreButton.textContent = item.actionLabel;

  const recycleButton = document.createElement("button");
  recycleButton.className = "mini-button quiet";
  recycleButton.type = "button";
  recycleButton.dataset.reviewInboxAction = "recycle-inbox-item";
  recycleButton.dataset.itemId = item.id;
  recycleButton.dataset.itemTitle = item.title;
  recycleButton.disabled = !item.id;
  recycleButton.textContent = "Recycle";

  actions.append(restoreButton, recycleButton);
  row.append(body, actions);
  return row;
}

function reviewRecycleBinItemRow(item) {
  const row = document.createElement("div");
  row.className = "review-task-row";
  attachItemDetail(row, item);

  const body = document.createElement("div");
  body.className = "review-task-body";
  const title = document.createElement("strong");
  title.textContent = item.title;
  const meta = document.createElement("span");
  meta.textContent = item.meta || item.description || "";
  body.append(title, meta);
  if (item.description && item.meta) {
    const description = document.createElement("span");
    description.textContent = item.description;
    body.append(description);
  }

  const actions = document.createElement("div");
  actions.className = "review-task-actions";
  const restoreButton = document.createElement("button");
  restoreButton.className = "mini-button";
  restoreButton.type = "button";
  restoreButton.dataset.reviewInboxAction = "restore-recycled-item";
  restoreButton.dataset.itemId = item.id;
  restoreButton.dataset.itemTitle = item.title;
  restoreButton.disabled = !item.id;
  restoreButton.textContent = item.actionLabel;

  const deleteButton = document.createElement("button");
  deleteButton.className = "mini-button danger";
  deleteButton.type = "button";
  deleteButton.dataset.reviewInboxAction = "delete-recycled-item";
  deleteButton.dataset.itemId = item.id;
  deleteButton.dataset.itemTitle = item.title;
  deleteButton.disabled = !item.id;
  deleteButton.textContent = "Delete permanently";

  actions.append(restoreButton, deleteButton);
  row.append(body, actions);
  return row;
}

function resetPendingRecycleDeleteButtons(exceptButton = null) {
  for (const button of elements.reviewRecycleBinItems.querySelectorAll(
    '[data-review-inbox-action="delete-recycled-item"][data-confirming-delete="true"]',
  )) {
    if (button === exceptButton) continue;

    const resetTimer = Number(button.dataset.confirmResetTimer || 0);
    if (resetTimer) window.clearTimeout(resetTimer);
    delete button.dataset.confirmResetTimer;
    button.removeAttribute("data-confirming-delete");
    button.classList.remove("is-confirming");
    button.textContent = "Delete permanently";
  }
}

function guidedCaptureDetails(item, projectOptions, projectTargetDate) {
  const details = document.createElement("details");
  details.className = "guided-details";

  const summary = document.createElement("summary");
  summary.textContent = "Clarify this item";

  const form = document.createElement("form");
  form.className = "guided-form";
  form.dataset.sourceTaskId = item.id;
  form.dataset.guidedStep = "type";
  const inferredCategory = inferGuidedProjectCategory(item.title, item.description);

  form.append(
    guidedStepHeader(),
    guidedStepSection(
      "type",
      decisionChoiceField(),
      decisionHelpDetails(),
    ),
    guidedStepSection(
      "describe",
      formField("Title", textInput("capture_text", item.title, "Action title")),
      formField(
        "Notes",
        textAreaInput(
          "description",
          item.description === "No notes yet." ? "" : item.description,
          "Useful context, constraints, or first thoughts",
        ),
      ),
    ),
    guidedStepSection(
      "details",
      formField("Existing project", projectSelect(projectOptions), "support-project-only"),
      formField("Horizon", selectInput("horizon", HORIZON_OPTIONS)),
      formField("Block type", selectInput("block_type", BLOCK_TYPE_OPTIONS), "task-only"),
      formField(
        "Minutes",
        textInput("duration_minutes", "", "Optional", "number"),
        "task-only",
      ),
      checkboxField("Mark as frog", "frog", false, "task-only"),
      formField(
        "Project category",
        selectInput("category", [
          ["work", "Work"],
          ["personal", "Personal"],
        ], inferredCategory),
        "project-only",
      ),
      formField(
        "Target date",
        textInput("target_date", projectTargetDate, "YYYY-MM-DD", "date"),
        "project-only",
      ),
      formField(
        "Success level",
        selectInput("level_of_success", SUCCESS_LEVEL_OPTIONS),
        "project-only",
      ),
      formField(
        "Why",
        textAreaInput("why_link_text", "", "Why does this deserve a project slot?"),
        "project-only",
      ),
      formField(
        "First chunk",
        textInput("first_chunk", "", "Optional first next action"),
        "project-only",
      ),
      checkboxField("Include this project this week", "include_this_week", true, "project-only"),
      checkboxField("Allow non-action project title", "verb_check_ack", false, "project-only"),
      formField(
        "Waiting person",
        textInput("waiting_person", "", "Who owns the next move?"),
        "opp-only",
      ),
      checkboxField("I have checked this deserves time or attention", "displacement_ack", true),
    ),
  );

  form.append(guidedStepActions());

  details.append(summary, form);
  syncGuidedForm(form);
  return details;
}

function inboxItemBody(item) {
  const body = document.createElement("div");
  body.className = "inbox-item-body";
  const title = document.createElement("strong");
  title.textContent = item.title;
  const description = document.createElement("span");
  description.textContent = item.description;
  const meta = document.createElement("small");
  meta.textContent = item.meta;
  body.append(title, description, meta);
  return body;
}

function buildInboxActions(item) {
  const actions = [];
  for (const [intent, label] of Object.entries(INBOX_ROUTE_ACTIONS)) {
    const button = document.createElement("button");
    button.className = "mini-button";
    button.type = "button";
    button.dataset.inboxAction = intent === "park_let_go" ? "park-menu" : "route";
    button.dataset.itemId = item.id;
    button.dataset.itemTitle = item.title;
    button.dataset.intent = intent;
    button.dataset.intentLabel = label;
    button.textContent = label;
    actions.push(button);
  }

  const recycle = document.createElement("button");
  recycle.className = "mini-button quiet";
  recycle.type = "button";
  recycle.dataset.inboxAction = "recycle";
  recycle.dataset.itemId = item.id;
  recycle.dataset.itemTitle = item.title;
  recycle.textContent = "Recycle";
  actions.push(recycle);
  return actions;
}

function parkChoicePanel(item) {
  const panel = document.createElement("form");
  panel.className = "park-choice-panel hidden";
  panel.dataset.parkPanel = item.id;

  const heading = document.createElement("div");
  heading.className = "compact-heading";
  const title = document.createElement("h3");
  title.textContent = "Park this item";
  const description = document.createElement("p");
  description.textContent =
    "Choose whether this disappears until a specific date and time, or stays parked for Review.";
  heading.append(title, description);

  const actions = document.createElement("div");
  actions.className = "park-choice-actions";
  const parkUntil = document.createElement("button");
  parkUntil.className = "primary-button";
  parkUntil.type = "submit";
  parkUntil.dataset.parkAction = "until";
  parkUntil.dataset.itemId = item.id;
  parkUntil.dataset.itemTitle = item.title;
  parkUntil.textContent = "Park until date/time";

  const parkWithoutDate = document.createElement("button");
  parkWithoutDate.className = "ghost-button";
  parkWithoutDate.type = "button";
  parkWithoutDate.dataset.parkAction = "without-date";
  parkWithoutDate.dataset.itemId = item.id;
  parkWithoutDate.dataset.itemTitle = item.title;
  parkWithoutDate.textContent = "Park without date";

  const cancel = document.createElement("button");
  cancel.className = "mini-button quiet";
  cancel.type = "button";
  cancel.dataset.parkAction = "cancel";
  cancel.textContent = "Cancel";

  actions.append(parkUntil, parkWithoutDate, cancel);
  panel.append(heading, parkCalendarControl(), actions);
  return panel;
}

function parkCalendarControl(referenceDate = new Date()) {
  const selectedDate = new Date(referenceDate);
  selectedDate.setDate(selectedDate.getDate() + 1);
  selectedDate.setHours(9, 0, 0, 0);

  const calendar = document.createElement("section");
  calendar.className = "park-calendar";
  calendar.dataset.parkCalendar = "true";
  calendar.dataset.viewMonth = parkMonthKey(selectedDate);
  calendar.dataset.selectedDate = parkDateKey(selectedDate);

  const header = document.createElement("div");
  header.className = "park-calendar-header";
  header.append(
    parkCalendarButton("Previous month", "previous-month", "<"),
    elementWithClass("strong", "park-calendar-month", ""),
    parkCalendarButton("Next month", "next-month", ">"),
  );

  const grid = document.createElement("div");
  grid.className = "park-calendar-grid";

  const timeLabel = document.createElement("label");
  timeLabel.className = "park-time-field";
  const timeText = document.createElement("span");
  timeText.textContent = "Return time";
  const timeInput = document.createElement("input");
  timeInput.type = "time";
  timeInput.name = "park_time";
  timeInput.value = "09:00";
  timeInput.required = true;
  timeLabel.append(timeText, timeInput);

  const hidden = document.createElement("input");
  hidden.type = "hidden";
  hidden.name = "park_until";

  calendar.append(header, grid, timeLabel, hidden);
  renderParkCalendar(calendar);
  return calendar;
}

function parkCalendarButton(label, action, text) {
  const button = document.createElement("button");
  button.className = "park-calendar-nav";
  button.type = "button";
  button.dataset.parkCalendarAction = action;
  button.ariaLabel = label;
  button.textContent = text;
  return button;
}

function renderParkCalendar(calendar) {
  const [year, month] = calendar.dataset.viewMonth.split("-").map(Number);
  const selectedDate = calendar.dataset.selectedDate;
  const monthDate = new Date(year, month - 1, 1);
  const monthTitle = calendar.querySelector(".park-calendar-month");
  const grid = calendar.querySelector(".park-calendar-grid");
  if (!monthTitle || !grid) return;

  monthTitle.textContent = new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
  }).format(monthDate);

  grid.replaceChildren();
  for (const weekday of PARK_CALENDAR_WEEKDAYS) {
    const label = document.createElement("span");
    label.className = "park-calendar-weekday";
    label.textContent = weekday.label;
    label.title = weekday.title;
    label.setAttribute("aria-label", weekday.title);
    grid.append(label);
  }

  const firstWeekday = (monthDate.getDay() + 6) % 7;
  for (let index = 0; index < firstWeekday; index += 1) {
    const blank = document.createElement("span");
    blank.className = "park-calendar-blank";
    grid.append(blank);
  }

  const daysInMonth = new Date(year, month, 0).getDate();
  const today = parkDateKey(new Date());
  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = new Date(year, month - 1, day);
    const dateKey = parkDateKey(date);
    const button = document.createElement("button");
    button.className = "park-calendar-day";
    button.type = "button";
    button.dataset.parkCalendarAction = "select-date";
    button.dataset.date = dateKey;
    button.textContent = String(day);
    button.classList.toggle("is-selected", dateKey === selectedDate);
    button.classList.toggle("is-today", dateKey === today);
    grid.append(button);
  }

  syncParkCalendarValue(calendar);
}

function handleParkCalendarAction(button) {
  const calendar = button.closest("[data-park-calendar]");
  if (!calendar) return;

  if (button.dataset.parkCalendarAction === "select-date") {
    calendar.dataset.selectedDate = button.dataset.date;
    calendar.dataset.viewMonth = button.dataset.date.slice(0, 7);
    renderParkCalendar(calendar);
    calendar.querySelector('[name="park_time"]')?.focus();
    return;
  }

  const offset = button.dataset.parkCalendarAction === "previous-month" ? -1 : 1;
  const [year, month] = calendar.dataset.viewMonth.split("-").map(Number);
  const nextMonth = new Date(year, month - 1 + offset, 1);
  calendar.dataset.viewMonth = parkMonthKey(nextMonth);
  renderParkCalendar(calendar);
}

function syncParkCalendarValue(calendar) {
  if (!calendar) return;
  const hidden = calendar.querySelector('[name="park_until"]');
  const timeInput = calendar.querySelector('[name="park_time"]');
  if (!hidden) return;
  hidden.value = `${calendar.dataset.selectedDate}T${timeInput?.value || "09:00"}`;
}

function parkMonthKey(date) {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}`;
}

function parkDateKey(date) {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`;
}

function padDatePart(value) {
  return String(value).padStart(2, "0");
}

function elementWithClass(tagName, className, textContent) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = textContent;
  return element;
}

function showParkChoicePanel(itemId) {
  for (const panel of elements.inboxItems.querySelectorAll(".park-choice-panel")) {
    const selected = panel.dataset.parkPanel === itemId;
    panel.classList.toggle("hidden", !selected);
    if (selected) {
      panel.querySelector(".park-calendar-day.is-selected")?.focus();
    }
  }
}

function hideParkChoicePanels() {
  for (const panel of elements.inboxItems.querySelectorAll(".park-choice-panel")) {
    panel.classList.add("hidden");
  }
}

async function submitParkRoute(itemId, itemTitle, parkedUntilValue = "") {
  await requestJson(
    window.fetch.bind(window),
    settings,
    `/api/v1/inbox/${encodeURIComponent(itemId)}/route`,
    {
      method: "POST",
      body: buildParkRoutePayload(parkedUntilValue),
    },
  );
  await connectAndLoad();
  const untilCopy = parkedUntilValue ? ` until ${parkedUntilValue.replace("T", " ")}` : "";
  showActionFeedback({
    message: `Parked "${itemTitle || "this item"}"${untilCopy}.`,
    undoPath: `/api/v1/inbox/${encodeURIComponent(itemId)}/undo`,
    undoLabel: "Undo",
    restoredMessage: `Restored "${itemTitle || "this item"}" to Inbox.`,
  });
}

function guidedStepHeader() {
  const header = document.createElement("div");
  header.className = "guided-stepper";
  return header;
}

function guidedStepSection(stepId, ...children) {
  const section = document.createElement("section");
  section.className = "guided-step";
  section.dataset.guidedStep = stepId;
  const heading = document.createElement("div");
  heading.className = "guided-step-heading";
  const title = document.createElement("strong");
  title.dataset.guidedStepHeading = "true";
  const description = document.createElement("span");
  description.dataset.guidedStepDescription = "true";
  heading.append(title, description);
  section.append(heading, ...children);
  return section;
}

function guidedStepActions() {
  const actions = document.createElement("div");
  actions.className = "guided-actions";

  const back = document.createElement("button");
  back.className = "mini-button quiet";
  back.type = "button";
  back.dataset.guidedAction = "back";
  back.textContent = "Back";

  const next = document.createElement("button");
  next.className = "mini-button";
  next.type = "button";
  next.dataset.guidedAction = "next";
  next.textContent = "Continue";

  const submit = document.createElement("button");
  submit.className = "primary-button";
  submit.type = "submit";
  submit.textContent = "Save decision";

  actions.append(back, next, submit);
  return actions;
}

function decisionChoiceField() {
  const fieldset = document.createElement("fieldset");
  fieldset.className = "decision-step";
  const legend = document.createElement("legend");
  legend.textContent = "What is this?";
  const grid = document.createElement("div");
  grid.className = "decision-card-grid";

  for (const [value, labelText] of DECISION_OPTIONS) {
    const label = document.createElement("label");
    label.className = "decision-card";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "decision";
    input.value = value;
    input.checked = value === "task";

    const body = document.createElement("span");
    body.className = "decision-card-body";
    const title = document.createElement("strong");
    title.textContent = labelText;
    body.append(title);
    label.append(input, body);
    grid.append(label);
  }

  fieldset.append(legend, grid);
  return fieldset;
}

function decisionHelpDetails() {
  const details = document.createElement("details");
  details.className = "decision-help";
  const summary = document.createElement("summary");
  summary.textContent = "Help me choose";
  const grid = document.createElement("div");
  grid.className = "decision-help-grid";

  for (const [, labelText, descriptionText] of DECISION_OPTIONS) {
    const item = document.createElement("div");
    item.className = "decision-help-row";
    const title = document.createElement("strong");
    title.textContent = labelText;
    const description = document.createElement("span");
    description.textContent = descriptionText;
    item.append(title, description);
    grid.append(item);
  }

  details.append(summary, grid);
  return details;
}

function formField(labelText, control, className = "") {
  const label = document.createElement("label");
  label.className = className;
  const labelSpan = document.createElement("span");
  labelSpan.textContent = labelText;
  label.append(labelSpan, control);
  return label;
}

function checkboxField(labelText, name, checked, className = "") {
  const label = document.createElement("label");
  label.className = `checkbox-field ${className}`.trim();
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = name;
  input.checked = checked;
  if (name === "displacement_ack") {
    input.required = true;
  }
  const text = document.createElement("span");
  text.textContent = labelText;
  label.append(input, text);
  return label;
}

function textInput(name, value, placeholder, type = "text") {
  const input = document.createElement("input");
  input.name = name;
  input.type = type;
  input.value = value || "";
  input.placeholder = placeholder || "";
  if (name === "capture_text") {
    input.required = true;
  }
  return input;
}

function requiredTextInput(name, value, placeholder, type = "text") {
  const input = textInput(name, value, placeholder, type);
  input.required = true;
  return input;
}

function textAreaInput(name, value, placeholder) {
  const textarea = document.createElement("textarea");
  textarea.name = name;
  textarea.value = value || "";
  textarea.placeholder = placeholder || "";
  return textarea;
}

function selectInput(name, options, selectedValue = "") {
  const select = document.createElement("select");
  select.name = name;
  for (const [value, label] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === selectedValue;
    select.append(option);
  }
  return select;
}

function projectSelect(projectOptions) {
  const select = document.createElement("select");
  select.name = "project_id";

  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = projectOptions.length
    ? "Choose project"
    : "No projects available";
  select.append(empty);

  for (const project of projectOptions) {
    const option = document.createElement("option");
    option.value = project.id;
    option.textContent = project.label;
    select.append(option);
  }
  return select;
}

function syncGuidedForm(form) {
  const decision = form.elements.decision.value || "task";
  const copy = guidedDecisionCopy(decision);
  const plan = guidedProcessStepPlan(decision);
  const stepIds = plan.map((step) => step.id);
  if (!stepIds.includes(form.dataset.guidedStep)) {
    form.dataset.guidedStep = stepIds[0];
  }

  form.dataset.decision = decision;
  const copyHeading = form.querySelector("[data-decision-copy-heading]");
  const copyDescription = form.querySelector("[data-decision-copy-description]");
  const submit = form.querySelector('button[type="submit"]');
  if (copyHeading) {
    copyHeading.textContent = copy.heading;
  }
  if (copyDescription) {
    copyDescription.textContent = copy.description;
  }
  if (submit) {
    submit.textContent = copy.submitLabel;
  }
  syncGuidedStepper(form, plan);
  syncGuidedSections(form, plan);
  syncGuidedActions(form, plan);

  setSectionState(form, "project-only", decision === "project");
  setSectionState(form, "support-project-only", decision === "task" || decision === "opp");
  setSectionState(form, "task-only", decision === "task");
  setSectionState(form, "opp-only", decision === "opp");

  if (form.elements.project_id) {
    form.elements.project_id.required = decision === "task" || decision === "opp";
  }
  if (form.elements.target_date) {
    form.elements.target_date.required = decision === "project";
  }
  if (form.elements.waiting_person) {
    form.elements.waiting_person.required = decision === "opp";
  }
}

function syncGuidedStepper(form, plan) {
  const stepper = form.querySelector(".guided-stepper");
  if (!stepper) return;

  stepper.replaceChildren();
  const currentIndex = guidedStepIndex(form, plan);
  for (const [index, step] of plan.entries()) {
    const pill = document.createElement("button");
    pill.className = "guided-step-pill";
    pill.type = "button";
    pill.dataset.guidedAction = "jump";
    pill.dataset.guidedStepTarget = step.id;
    pill.classList.toggle("is-active", step.id === form.dataset.guidedStep);
    pill.classList.toggle("is-complete", index < currentIndex);
    pill.disabled = index > currentIndex + 1;
    pill.textContent = `${index + 1}. ${step.label}`;
    stepper.append(pill);
  }
}

function syncGuidedSections(form, plan) {
  for (const section of form.querySelectorAll(".guided-step")) {
    const step = plan.find((item) => item.id === section.dataset.guidedStep);
    const active = section.dataset.guidedStep === form.dataset.guidedStep;
    section.classList.toggle("hidden", !active);
    const heading = section.querySelector("[data-guided-step-heading]");
    const description = section.querySelector("[data-guided-step-description]");
    if (heading) {
      heading.textContent = step?.heading || "";
    }
    if (description) {
      description.textContent = step?.description || "";
    }
  }
}

function syncGuidedActions(form, plan) {
  const index = guidedStepIndex(form, plan);
  const lastIndex = plan.length - 1;
  const back = form.querySelector('[data-guided-action="back"]');
  const next = form.querySelector('[data-guided-action="next"]');
  const submit = form.querySelector('button[type="submit"]');

  if (back) {
    back.classList.toggle("hidden", index === 0);
  }
  if (next) {
    next.classList.toggle("hidden", index === lastIndex);
  }
  if (submit) {
    submit.classList.toggle("hidden", index !== lastIndex);
  }
}

function guidedStepIndex(form, plan) {
  return Math.max(0, plan.findIndex((step) => step.id === form.dataset.guidedStep));
}

function setGuidedStep(form, nextStepId) {
  const plan = guidedProcessStepPlan(form.elements.decision.value || "task");
  const step = plan.find((item) => item.id === nextStepId);
  form.dataset.guidedStep = step ? step.id : plan[0].id;
  syncGuidedForm(form);
}

function validateGuidedStep(form) {
  const section = currentGuidedStepSection(form);
  if (!section) return true;
  for (const control of section.querySelectorAll("input, select, textarea")) {
    if (!control.disabled && !control.checkValidity()) {
      control.reportValidity();
      return false;
    }
  }
  return true;
}

function currentGuidedStepSection(form) {
  return form.querySelector(`.guided-step[data-guided-step="${form.dataset.guidedStep}"]`);
}

function setSectionState(form, className, enabled) {
  for (const element of form.querySelectorAll(`.${className}`)) {
    element.classList.toggle("hidden", !enabled);
    for (const control of element.querySelectorAll("input, select, textarea")) {
      control.disabled = !enabled;
    }
  }
}

function ritualStatusText(rituals) {
  const complete = [
    rituals.morning ? "Morning" : "",
    rituals.midday ? "Midday" : "",
    rituals.evening ? "Evening" : "",
  ].filter(Boolean);
  if (rituals.nextLabel) {
    return complete.length
      ? `${complete.join(", ")} done · next ${rituals.nextLabel}`
      : `Next ${rituals.nextLabel}`;
  }
  return complete.length ? `${complete.join(", ")} done` : "Not started";
}

function countPill(label, value) {
  const pill = document.createElement("div");
  pill.className = "count-pill";
  pill.innerHTML = `<span>${label}</span><strong>${Number(value || 0)}</strong>`;
  return pill;
}

function renderItems(container, items, emptyText) {
  container.replaceChildren();
  if (!items.length) {
    container.append(emptyState(emptyText));
    return;
  }

  for (const item of items.slice(0, 6)) {
    const row = document.createElement("div");
    row.className = "list-row";
    attachItemDetail(row, item);
    const title = document.createElement("strong");
    title.textContent = item.title;
    const meta = document.createElement("span");
    meta.textContent = item.meta || item.description || "";
    row.append(title, meta);
    container.append(row);
  }
}

function renderTodayTasks(container, tasks) {
  container.replaceChildren();
  if (!tasks.length) {
    container.append(emptyState("No Today tasks yet."));
    return;
  }

  for (const task of tasks.slice(0, 6)) {
    const row = document.createElement("div");
    row.className = "list-row today-task-row";
    row.classList.toggle("is-complete", Boolean(task.completed));
    attachItemDetail(row, task);

    const body = document.createElement("div");
    body.className = "list-row-body";
    const title = document.createElement("strong");
    title.textContent = task.title;
    const meta = document.createElement("span");
    meta.textContent = [
      task.meta || task.description || "",
      task.completed ? "Done" : "",
    ].filter(Boolean).join(" · ");
    body.append(title, meta);

    const button = document.createElement("button");
    button.className = task.completed ? "mini-button quiet" : "mini-button";
    button.type = "button";
    button.dataset.todayTaskAction = task.lifecycleAction;
    button.dataset.taskId = task.id;
    button.dataset.taskTitle = task.title;
    button.disabled = !task.id;
    button.textContent = task.lifecycleLabel || (task.completed ? "Reopen" : "Complete");

    row.append(body, button);
    container.append(row);
  }
}

function renderBlocks(container, blocks) {
  container.replaceChildren();
  if (!blocks.length) {
    container.append(emptyState("No blocks scheduled today."));
    return;
  }

  for (const block of blocks) {
    const card = document.createElement("div");
    card.className = "block-card";
    const time = document.createElement("span");
    time.textContent = block.time || "Any time";
    const title = document.createElement("strong");
    title.textContent = block.title;
    const meta = document.createElement("span");
    meta.textContent = block.meta;
    card.append(time, title, meta);
    container.append(card);
  }
}

function emptyState(text) {
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = text;
  return empty;
}

function clearActionFeedback() {
  elements.actionFeedback.replaceChildren();
  elements.actionFeedback.classList.add("hidden");
}

function showActionFeedback(feedback) {
  clearActionFeedback();
  if (!feedback?.message) {
    return;
  }

  const message = document.createElement("span");
  message.textContent = feedback.message;
  elements.actionFeedback.append(message);

  if (feedback.undoPath) {
    const undo = document.createElement("button");
    undo.className = "mini-button quiet";
    undo.type = "button";
    undo.dataset.feedbackAction = "undo";
    undo.dataset.undoPath = feedback.undoPath;
    undo.dataset.restoredMessage = feedback.restoredMessage;
    undo.textContent = feedback.undoLabel || "Undo";
    elements.actionFeedback.append(undo);
  }

  elements.actionFeedback.classList.remove("hidden");
}

for (const tab of elements.workflowTabs) {
  tab.addEventListener("click", async () => {
    const nextWorkflow = tab.dataset.workflowTab;
    clearActionFeedback();
    setWorkflow(nextWorkflow);
    try {
      await refreshWorkflowData(nextWorkflow);
    } catch (err) {
      setConnectionState(
        "error",
        "Refresh failed",
        err instanceof Error ? err.message : String(err),
      );
    }
  });
}

elements.globalSearchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  performGlobalSearch();
});

elements.globalSearchInput.addEventListener("input", () => {
  scheduleGlobalSearch();
});

elements.globalSearchIncludeRecycle.addEventListener("change", () => {
  if (elements.globalSearchInput.value.trim()) {
    performGlobalSearch();
  }
});

elements.globalSearchResults.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-search-result-workflow]");
  if (!button) return;

  hideGlobalSearchResults();
  elements.globalSearchInput.blur();
  openItemDetail(searchResultDetail(button));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    hideGlobalSearchResults();
    if (itemDetailOpen) {
      closeItemDetail();
    }
  }

  if (event.key === "Enter" || event.key === " ") {
    const trigger = event.target.closest?.("[data-item-detail]");
    if (!trigger || isItemDetailInteractiveTarget(event.target)) return;

    event.preventDefault();
    openItemDetail(itemDetailFromElement(trigger));
  }
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".global-search")) {
    hideGlobalSearchResults();
  }
});

document.addEventListener("click", async (event) => {
  if (event.target.closest("[data-item-detail-close]")) {
    closeItemDetail();
    return;
  }

  const actionButton = event.target.closest("[data-item-detail-action-id]");
  if (!actionButton) return;
  await performItemDetailAction(actionButton);
});

document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-item-detail]");
  if (!trigger || isItemDetailInteractiveTarget(event.target)) return;

  openItemDetail(itemDetailFromElement(trigger));
});

elements.itemDetailEditForm.addEventListener("submit", saveItemDetailEdit);

elements.connectionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    settings = {
      serverUrl: elements.serverUrl.value,
      apiToken: elements.apiToken.value,
    };
    await saveSettings(window.localStorage, settings, tauriInvoke);
    settings = await loadSettings(window.localStorage, tauriInvoke);
    connectAndLoad();
  } catch (err) {
    setConnectionState("error", "Invalid connection settings", err.message);
    setWorkflow("settings");
  }
});

elements.connectionForm.addEventListener("input", () => {
  lastAuthRequired = null;
  renderConnectionGuidance(null);
});

elements.resetSettings.addEventListener("click", async () => {
  await clearSettings(window.localStorage, tauriInvoke);
  settings = await loadSettings(window.localStorage, tauriInvoke);
  lastAuthRequired = null;
  applySettingsToForm();
  connectAndLoad();
});

elements.refreshDashboard.addEventListener("click", () => {
  connectAndLoad();
});

elements.reviewRefresh.addEventListener("click", async () => {
  elements.reviewRefresh.disabled = true;
  try {
    await reloadWeeklyReview();
    showActionFeedback({ message: "Weekly review refreshed." });
  } catch (err) {
    setConnectionState("error", "Weekly review refresh failed", err.message);
  } finally {
    elements.reviewRefresh.disabled = false;
  }
});

elements.quickCaptureForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const verbNoun = elements.quickCaptureInput.value.trim();
  if (!verbNoun) return;

  elements.quickCaptureInput.disabled = true;
  try {
    await requestJson(window.fetch.bind(window), settings, "/api/v1/inbox/quick-capture", {
      method: "POST",
      body: { verb_noun: verbNoun },
    });
    elements.quickCaptureInput.value = "";
    await connectAndLoad();
    showActionFeedback({
      message: `Captured "${verbNoun}" to Inbox.`,
      undoPath: "",
      undoLabel: "",
      restoredMessage: "",
    });
  } catch (err) {
    setConnectionState("error", "Quick capture failed", err.message);
  } finally {
    elements.quickCaptureInput.disabled = false;
    elements.quickCaptureInput.focus();
  }
});

elements.dailyFocusForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  elements.oneThingInput.disabled = true;
  elements.frogInput.disabled = true;
  try {
    await requestJson(window.fetch.bind(window), settings, "/api/v1/daily-focus", {
      method: "PUT",
      body: {
        one_thing: elements.oneThingInput.value,
        frog: elements.frogInput.value,
      },
    });
    await connectAndLoad();
    showActionFeedback({
      message: "Saved today's focus.",
      undoPath: "",
      undoLabel: "",
      restoredMessage: "",
    });
  } catch (err) {
    setConnectionState("error", "Daily focus save failed", err.message);
  } finally {
    elements.oneThingInput.disabled = false;
    elements.frogInput.disabled = false;
  }
});

elements.todayTasks.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-today-task-action]");
  if (!button) return;

  const action = button.dataset.todayTaskAction;
  const taskId = button.dataset.taskId;
  if (!taskId || !["complete", "reopen"].includes(action)) return;

  button.disabled = true;
  try {
    const feedback = buildTodayTaskActionFeedback({
      action,
      taskId,
      taskTitle: button.dataset.taskTitle,
    });
    await requestJson(
      window.fetch.bind(window),
      settings,
      `/api/v1/tasks/${encodeURIComponent(taskId)}/${action}`,
      { method: "POST" },
    );
    await connectAndLoad();
    showActionFeedback(feedback);
  } catch (err) {
    setConnectionState("error", "Today task update failed", err.message);
  } finally {
    button.disabled = false;
  }
});

for (const container of [
  elements.reviewWeeklyProjects,
  elements.reviewFocusCandidates,
  elements.reviewResurfaceDue,
  elements.reviewCompletedTasks,
  elements.reviewLearningItems,
  elements.reviewEnjoyItems,
  elements.reviewParkedItems,
  elements.reviewRecycleBinItems,
]) {
  container.addEventListener("click", async (event) => {
    const inboxButton = event.target.closest("[data-review-inbox-action]");
    if (inboxButton) {
      const itemId = inboxButton.dataset.itemId;
      const itemTitle = inboxButton.dataset.itemTitle;
      if (!itemId) return;

      inboxButton.disabled = true;
      try {
        const action = inboxButton.dataset.reviewInboxAction;
        const feedback = buildWeeklyReviewActionFeedback(action, itemTitle);
        if (action === "delete-recycled-item") {
          if (inboxButton.getAttribute("data-confirming-delete") !== "true") {
            resetPendingRecycleDeleteButtons(inboxButton);
            inboxButton.setAttribute("data-confirming-delete", "true");
            inboxButton.classList.add("is-confirming");
            inboxButton.textContent = "Confirm delete";
            const resetTimer = window.setTimeout(() => {
              resetPendingRecycleDeleteButtons();
            }, 5000);
            inboxButton.dataset.confirmResetTimer = String(resetTimer);
            inboxButton.disabled = false;
            return;
          }

          const resetTimer = Number(inboxButton.dataset.confirmResetTimer || 0);
          if (resetTimer) window.clearTimeout(resetTimer);
          delete inboxButton.dataset.confirmResetTimer;
          await requestJson(
            window.fetch.bind(window),
            settings,
            `/api/v1/tasks/${encodeURIComponent(itemId)}`,
            { method: "DELETE" },
          );
          await refreshDashboardAndReview();
          showActionFeedback(feedback);
          return;
        }

        const endpointAction = action === "recycle-inbox-item" ? "recycle" : "restore";
        await requestJson(
          window.fetch.bind(window),
          settings,
          `/api/v1/inbox/${encodeURIComponent(itemId)}/${endpointAction}`,
          { method: "POST" },
        );
        await refreshDashboardAndReview();
        if (action === "recycle-inbox-item") {
          showActionFeedback({
            message: feedback.message,
            undoPath: `/api/v1/inbox/${encodeURIComponent(itemId)}/restore`,
            undoLabel: feedback.undo?.label || "Restore",
            restoredMessage: `Restored "${itemTitle || "this item"}".`,
          });
          return;
        }
        showActionFeedback(feedback);
      } catch (err) {
        setConnectionState("error", "Review item update failed", err.message);
      } finally {
        inboxButton.disabled = false;
      }
      return;
    }

    const button = event.target.closest("[data-review-action]");
    if (!button) return;

    button.disabled = true;
    try {
      if (button.dataset.reviewAction === "toggle-project-card") {
        const projectId = button.dataset.projectId;
        const detail = button.closest(".review-card")?.querySelector("[data-project-card-detail]");
        if (!projectId || !detail) return;

        if (!detail.classList.contains("hidden")) {
          detail.classList.add("hidden");
          return;
        }

        if (detail.dataset.loaded !== "true") {
          const card = await requestJson(
            window.fetch.bind(window),
            settings,
            `/api/v1/projects/${encodeURIComponent(projectId)}/card`,
          );
          renderProjectCardDetail(detail, card);
        }
        detail.classList.remove("hidden");
        return;
      }

      if (button.dataset.reviewAction === "focus-toggle") {
        const projectId = button.dataset.projectId;
        const nextActive = button.dataset.nextActive === "true";
        if (!projectId) return;

        await requestJson(
          window.fetch.bind(window),
          settings,
          `/api/v1/projects/${encodeURIComponent(projectId)}`,
          {
            method: "PATCH",
            body: { active_this_week: nextActive },
          },
        );
        await refreshDashboardAndReview();
        showActionFeedback(
          buildWeeklyReviewActionFeedback(
            nextActive ? "focus-on" : "focus-off",
            button.dataset.projectTitle,
          ),
        );
        return;
      }

      const taskId = button.dataset.taskId;
      if (!taskId) return;

      if (button.dataset.reviewAction === "move-to-week") {
        await requestJson(
          window.fetch.bind(window),
          settings,
          `/api/v1/weekly-review/tasks/${encodeURIComponent(taskId)}/move-to-week`,
          { method: "POST" },
        );
        await refreshDashboardAndReview();
        showActionFeedback(
          buildWeeklyReviewActionFeedback("move-to-week", button.dataset.taskTitle),
        );
        return;
      }

      if (button.dataset.reviewAction === "archive-task") {
        const feedback = buildWeeklyReviewActionFeedback("archive", button.dataset.taskTitle);
        await requestJson(
          window.fetch.bind(window),
          settings,
          `/api/v1/tasks/${encodeURIComponent(taskId)}/archive`,
          { method: "POST" },
        );
        await refreshDashboardAndReview();
        showActionFeedback({
          message: feedback.message,
          undoPath: `/api/v1/tasks/${encodeURIComponent(taskId)}/restore`,
          undoLabel: feedback.undo?.label || "Restore",
          restoredMessage: `Restored "${button.dataset.taskTitle || "this task"}".`,
        });
      }
    } catch (err) {
      setConnectionState("error", "Weekly review action failed", err.message);
    } finally {
      button.disabled = false;
    }
  });
}

for (const container of [elements.reviewWeeklyProjects, elements.reviewFocusCandidates]) {
  container.addEventListener("submit", async (event) => {
    const cardForm = event.target.closest(".project-card-form");
    const chunkForm = event.target.closest(".project-chunk-form");
    if (!cardForm && !chunkForm) return;
    event.preventDefault();

    const form = cardForm || chunkForm;
    const projectId = form.dataset.projectId;
    const detail = form.closest("[data-project-card-detail]");
    const submit = form.querySelector('button[type="submit"]');
    if (!projectId || !detail || !submit) return;

    submit.disabled = true;
    try {
      if (cardForm) {
        const payload = buildProjectCardPayload(Object.fromEntries(new FormData(cardForm).entries()));
        const card = await requestJson(
          window.fetch.bind(window),
          settings,
          `/api/v1/projects/${encodeURIComponent(projectId)}/card`,
          { method: "PUT", body: payload },
        );
        renderProjectCardDetail(detail, card);
        detail.classList.remove("hidden");
        showActionFeedback({ message: "Saved project card." });
        return;
      }

      const values = Object.fromEntries(new FormData(chunkForm).entries());
      const duration = Number(values.duration_minutes || 0);
      await requestJson(
        window.fetch.bind(window),
        settings,
        `/api/v1/projects/${encodeURIComponent(projectId)}/chunks`,
        {
          method: "POST",
          body: {
            verb_noun: values.verb_noun,
            duration_minutes: Number.isFinite(duration) && duration > 0 ? duration : undefined,
          },
        },
      );
      const card = await requestJson(
        window.fetch.bind(window),
        settings,
        `/api/v1/projects/${encodeURIComponent(projectId)}/card`,
      );
      renderProjectCardDetail(detail, card);
      detail.classList.remove("hidden");
      showActionFeedback({ message: "Added project chunk." });
    } catch (err) {
      setConnectionState("error", "Project card update failed", err.message);
    } finally {
      submit.disabled = false;
    }
  });
}

elements.processWorkflow.addEventListener("click", async (event) => {
  const guidedButton = event.target.closest("[data-guided-action]");
  if (guidedButton) {
    const form = guidedButton.closest(".guided-form");
    if (!form) return;
    const plan = guidedProcessStepPlan(form.elements.decision.value || "task");
    const index = guidedStepIndex(form, plan);

    if (guidedButton.dataset.guidedAction === "back") {
      setGuidedStep(form, plan[Math.max(0, index - 1)].id);
      return;
    }
    if (guidedButton.dataset.guidedAction === "next") {
      if (validateGuidedStep(form)) {
        setGuidedStep(form, plan[Math.min(plan.length - 1, index + 1)].id);
      }
      return;
    }
    if (guidedButton.dataset.guidedAction === "jump") {
      if (guidedButton.dataset.guidedStepTarget === form.dataset.guidedStep) return;
      const targetIndex = plan.findIndex(
        (step) => step.id === guidedButton.dataset.guidedStepTarget,
      );
      const canMoveBack = targetIndex >= 0 && targetIndex < index;
      const canMoveForward = targetIndex === index + 1 && validateGuidedStep(form);
      if (canMoveBack || canMoveForward) {
        setGuidedStep(form, guidedButton.dataset.guidedStepTarget);
      }
      return;
    }
  }

  const calendarButton = event.target.closest("[data-park-calendar-action]");
  if (calendarButton) {
    event.preventDefault();
    handleParkCalendarAction(calendarButton);
    return;
  }

  const parkButton = event.target.closest("[data-park-action]");
  if (parkButton && parkButton.dataset.parkAction !== "until") {
    if (parkButton.dataset.parkAction === "cancel") {
      hideParkChoicePanels();
      return;
    }

    const itemId = parkButton.dataset.itemId;
    if (!itemId) return;
    parkButton.disabled = true;
    try {
      await submitParkRoute(itemId, parkButton.dataset.itemTitle, "");
    } catch (err) {
      setConnectionState("error", "Park action failed", err.message);
    } finally {
      parkButton.disabled = false;
    }
    return;
  }

  const button = event.target.closest("[data-inbox-action]");
  if (!button) return;

  const itemId = button.dataset.itemId;
  if (!itemId) return;

  if (button.dataset.inboxAction === "park-menu") {
    showParkChoicePanel(itemId);
    return;
  }

  button.disabled = true;
  try {
    const feedback = buildInboxActionFeedback({
      action: button.dataset.inboxAction,
      itemId,
      itemTitle: button.dataset.itemTitle,
      intentLabel: button.dataset.intentLabel,
    });
    if (button.dataset.inboxAction === "route") {
      await requestJson(
        window.fetch.bind(window),
        settings,
        `/api/v1/inbox/${encodeURIComponent(itemId)}/route`,
        {
          method: "POST",
          body: { intent: button.dataset.intent },
        },
      );
    } else {
      await requestJson(
        window.fetch.bind(window),
        settings,
        `/api/v1/inbox/${encodeURIComponent(itemId)}/recycle`,
        { method: "POST" },
      );
    }
    await connectAndLoad();
    showActionFeedback(feedback);
  } catch (err) {
    setConnectionState("error", "Inbox action failed", err.message);
  } finally {
    button.disabled = false;
  }
});

elements.processWorkflow.addEventListener("change", (event) => {
  if (event.target.matches('[name="decision"]')) {
    syncGuidedForm(event.target.closest("form"));
    return;
  }

  if (event.target.matches('[name="park_time"]')) {
    syncParkCalendarValue(event.target.closest("[data-park-calendar]"));
  }
});

elements.processWorkflow.addEventListener("input", (event) => {
  if (event.target.matches('[name="park_time"]')) {
    syncParkCalendarValue(event.target.closest("[data-park-calendar]"));
  }
});

elements.processWorkflow.addEventListener("submit", async (event) => {
  const parkForm = event.target.closest(".park-choice-panel");
  if (parkForm) {
    event.preventDefault();
    const submit = parkForm.querySelector('[data-park-action="until"]');
    const itemId = submit?.dataset.itemId;
    if (!itemId) return;

    submit.disabled = true;
    try {
      const values = Object.fromEntries(new FormData(parkForm).entries());
      await submitParkRoute(itemId, submit.dataset.itemTitle, values.park_until);
    } catch (err) {
      setConnectionState("error", "Park action failed", err.message);
    } finally {
      submit.disabled = false;
    }
    return;
  }

  const form = event.target.closest(".guided-form");
  if (!form) return;
  event.preventDefault();

  const values = Object.fromEntries(new FormData(form).entries());
  const payload = buildGuidedCapturePayload(
    values.decision,
    form.dataset.sourceTaskId,
    values,
  );
  const submit = form.querySelector('button[type="submit"]');

  submit.disabled = true;
  try {
    await requestJson(window.fetch.bind(window), settings, "/api/v1/capture/guided", {
      method: "POST",
      body: payload,
    });
    const feedback = buildGuidedCaptureFeedback(values.decision, values.capture_text);
    await connectAndLoad();
    showActionFeedback(feedback);
  } catch (err) {
    setConnectionState("error", "Guided capture failed", err.message);
  } finally {
    submit.disabled = false;
  }
});

elements.actionFeedback.addEventListener("click", async (event) => {
  const button = event.target.closest('[data-feedback-action="undo"]');
  if (!button) return;

  const undoPath = button.dataset.undoPath;
  if (!undoPath) return;

  button.disabled = true;
  try {
    await requestJson(window.fetch.bind(window), settings, undoPath, { method: "POST" });
    await connectAndLoad();
    showActionFeedback({
      message: button.dataset.restoredMessage || "Restored item to Inbox.",
      undoPath: "",
      undoLabel: "",
      restoredMessage: "",
    });
  } catch (err) {
    setConnectionState("error", "Undo failed", err.message);
  } finally {
    button.disabled = false;
  }
});

async function initialize() {
  try {
    settings = await loadSettings(window.localStorage, tauriInvoke);
    renderCaptureWorkflow();
    applySettingsToForm();
    await connectAndLoad({ startupRetry: true });
  } catch (err) {
    setConnectionState(
      "error",
      "Secure token storage unavailable",
      err instanceof Error ? err.message : String(err),
    );
    setWorkflow("settings");
  }
}

initialize();
