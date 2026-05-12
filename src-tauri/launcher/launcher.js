import {
  WORKFLOWS,
  buildCaptureWorkflowViewModel,
  buildConnectionGuidance,
  buildGuidedCaptureFeedback,
  buildGuidedCapturePayload,
  buildInboxActionFeedback,
  buildProcessWorkflowViewModel,
  buildProjectOptions,
  buildBootstrapViewModel,
  buildTodayTaskActionFeedback,
  buildWeeklyReviewActionFeedback,
  buildWeeklyReviewViewModel,
  clearSettings,
  defaultGuidedProjectTargetDate,
  getTauriInvoke,
  guidedDecisionCopy,
  guidedProcessStepPlan,
  inferGuidedProjectCategory,
  loadSettings,
  requestJson,
  saveSettings,
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
  reviewFocusCandidates: document.getElementById("review-focus-candidates"),
  reviewResurfaceDue: document.getElementById("review-resurface-due"),
  reviewCompletedTasks: document.getElementById("review-completed-tasks"),
};

const tauriInvoke = getTauriInvoke(window);
let settings = {
  serverUrl: elements.serverUrl.value,
  apiToken: "",
};
let lastAuthRequired = null;
let activeWorkflow = "today";

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

async function connectAndLoad() {
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
    renderWeeklyReview(buildWeeklyReviewViewModel(weeklyReview));
    setConnectionState(
      "ready",
      auth?.auth_required ? "Connected with API token" : "Connected without auth",
      `${settings.serverUrl} · database ${summary?.system?.database_status || "unknown"}`,
    );
  } catch (err) {
    setConnectionState(
      "error",
      "Connection needs attention",
      err instanceof Error ? err.message : String(err),
    );
    setWorkflow("settings");
  }
}

async function refreshDashboardAndReview() {
  const [summary, weeklyReview] = await Promise.all([
    requestJson(window.fetch.bind(window), settings, "/api/v1/bootstrap"),
    requestJson(window.fetch.bind(window), settings, "/api/v1/weekly-review"),
  ]);
  renderDashboard(buildBootstrapViewModel(summary));
  renderWeeklyReview(buildWeeklyReviewViewModel(weeklyReview));
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
  const weeklyReview = await requestJson(
    window.fetch.bind(window),
    settings,
    "/api/v1/weekly-review",
  );
  renderWeeklyReview(buildWeeklyReviewViewModel(weeklyReview));
}

function renderDashboard(model) {
  elements.dashboard.classList.remove("hidden");
  elements.todayLabel.textContent = model.currentTime
    ? `${model.todayLabel} · ${model.currentTime}`
    : model.todayLabel;
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
  elements.inboxCounts.replaceChildren(
    countPill("Inbox", model.inbox.unprocessed),
    countPill("Learning", model.inbox.learn_explore),
    countPill("Enjoy", model.inbox.enjoy_recover),
    countPill("Parked", model.inbox.park_let_go),
    countPill("Recycle", model.inbox.recycle_bin),
  );
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
  elements.inboxItems.replaceChildren();
  if (!model.queue.length) {
    elements.inboxItems.append(emptyState("Inbox is clear. Capture something when it appears."));
    return;
  }

  for (const item of model.queue) {
    const row = document.createElement("div");
    row.className = "inbox-item";
    row.classList.toggle("process-primary", item.id === model.activeItem?.id);
    row.classList.toggle("process-queue", item.id !== model.activeItem?.id);

    const body = document.createElement("div");
    body.className = "inbox-item-body";
    const title = document.createElement("strong");
    title.textContent = item.title;
    const description = document.createElement("span");
    description.textContent = item.description;
    const meta = document.createElement("small");
    meta.textContent = item.meta;
    body.append(title, description, meta);

    const actions = document.createElement("div");
    actions.className = "inbox-actions";
    for (const [intent, label] of Object.entries(INBOX_ROUTE_ACTIONS)) {
      const button = document.createElement("button");
      button.className = "mini-button";
      button.type = "button";
      button.dataset.inboxAction = "route";
      button.dataset.itemId = item.id;
      button.dataset.itemTitle = item.title;
      button.dataset.intent = intent;
      button.dataset.intentLabel = label;
      button.textContent = label;
      actions.append(button);
    }

    const recycle = document.createElement("button");
    recycle.className = "mini-button quiet";
    recycle.type = "button";
    recycle.dataset.inboxAction = "recycle";
    recycle.dataset.itemId = item.id;
    recycle.dataset.itemTitle = item.title;
    recycle.textContent = "Recycle";
    actions.append(recycle);

    row.append(body, actions, guidedCaptureDetails(item, projectOptions, projectTargetDate));
    elements.inboxItems.append(row);
  }
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
  card.append(body);

  if (action) {
    const actions = document.createElement("div");
    actions.className = "review-card-actions";
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
    card.append(actions);
  }

  return card;
}

function reviewTaskRow(task, action) {
  const row = document.createElement("div");
  row.className = "review-task-row";

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

function guidedCaptureDetails(item, projectOptions, projectTargetDate) {
  const details = document.createElement("details");
  details.className = "guided-details";

  const summary = document.createElement("summary");
  summary.textContent = "Clarify into Task / Project / OPP";

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
      decisionCopyPanel(),
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
  legend.textContent = "Step 1 · choose the right kind of follow-up";
  const grid = document.createElement("div");
  grid.className = "decision-card-grid";

  for (const [value, labelText, descriptionText] of DECISION_OPTIONS) {
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
    const description = document.createElement("small");
    description.textContent = descriptionText;
    body.append(title, description);
    label.append(input, body);
    grid.append(label);
  }

  fieldset.append(legend, grid);
  return fieldset;
}

function decisionCopyPanel(decision = "task") {
  const copy = guidedDecisionCopy(decision);
  const panel = document.createElement("div");
  panel.className = "decision-copy";
  const heading = document.createElement("strong");
  heading.dataset.decisionCopyHeading = "true";
  heading.textContent = copy.heading;
  const description = document.createElement("span");
  description.dataset.decisionCopyDescription = "true";
  description.textContent = copy.description;
  panel.append(heading, description);
  return panel;
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
  elements.reviewFocusCandidates,
  elements.reviewResurfaceDue,
  elements.reviewCompletedTasks,
]) {
  container.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-review-action]");
    if (!button) return;

    button.disabled = true;
    try {
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

elements.inboxItems.addEventListener("click", async (event) => {
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

  const button = event.target.closest("[data-inbox-action]");
  if (!button) return;

  const itemId = button.dataset.itemId;
  if (!itemId) return;

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

elements.inboxItems.addEventListener("change", (event) => {
  if (!event.target.matches('[name="decision"]')) return;
  syncGuidedForm(event.target.closest("form"));
});

elements.inboxItems.addEventListener("submit", async (event) => {
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
    await connectAndLoad();
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
