import {
  buildInboxProcessingViewModel,
  buildBootstrapViewModel,
  clearSettings,
  loadSettings,
  requestJson,
  saveSettings,
} from "./client.js";

const INBOX_ROUTE_ACTIONS = {
  learn_explore: "Learning",
  enjoy_recover: "Enjoy",
  park_let_go: "Park",
};

const elements = {
  statusDot: document.getElementById("status-dot"),
  status: document.getElementById("status"),
  detail: document.getElementById("detail"),
  connectionCard: document.getElementById("connection-card"),
  connectionForm: document.getElementById("connection-form"),
  serverUrl: document.getElementById("server-url"),
  apiToken: document.getElementById("api-token"),
  resetSettings: document.getElementById("reset-settings"),
  dashboard: document.getElementById("dashboard"),
  refreshDashboard: document.getElementById("refresh-dashboard"),
  todayLabel: document.getElementById("today-label"),
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
  ritualStatus: document.getElementById("ritual-status"),
  waitingSummary: document.getElementById("waiting-summary"),
  todayTasks: document.getElementById("today-tasks"),
  weeklyProjects: document.getElementById("weekly-projects"),
  todayBlocks: document.getElementById("today-blocks"),
};

let settings = loadSettings(window.localStorage);

function setConnectionState(state, message, detail = "") {
  elements.statusDot.dataset.state = state;
  elements.status.textContent = message;
  elements.detail.textContent = detail;
}

function applySettingsToForm() {
  elements.serverUrl.value = settings.serverUrl;
  elements.apiToken.value = settings.apiToken;
}

async function connectAndLoad() {
  saveSettings(window.localStorage, settings);
  applySettingsToForm();
  setConnectionState("loading", "Checking Rust server...", settings.serverUrl);

  try {
    const health = await requestJson(window.fetch.bind(window), settings, "/healthz");
    if (health?.status !== "ok") {
      throw new Error(health?.detail || "Server health check did not report ok");
    }

    const auth = await requestJson(window.fetch.bind(window), settings, "/api/v1/auth/status");
    if (auth?.auth_required && !settings.apiToken) {
      elements.dashboard.classList.add("hidden");
      throw new Error("This server requires an API token.");
    }

    const [summary, inboxContainers] = await Promise.all([
      requestJson(window.fetch.bind(window), settings, "/api/v1/bootstrap"),
      requestJson(window.fetch.bind(window), settings, "/api/v1/inbox/containers"),
    ]);
    renderDashboard(buildBootstrapViewModel(summary));
    renderInboxProcessing(buildInboxProcessingViewModel(inboxContainers));
    setConnectionState(
      "ready",
      auth?.auth_required ? "Connected with API token" : "Connected without auth",
      `${settings.serverUrl} · database ${summary?.system?.database_status || "unknown"}`,
    );
  } catch (err) {
    elements.dashboard.classList.add("hidden");
    setConnectionState(
      "error",
      "Connection needs attention",
      err instanceof Error ? err.message : String(err),
    );
  }
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
  renderItems(elements.todayTasks, model.todayTasks, "No Today tasks yet.");
  renderItems(elements.weeklyProjects, model.weeklyProjects, "No weekly projects selected.");
  renderBlocks(elements.todayBlocks, model.todayBlocks);
}

function renderInboxProcessing(model) {
  elements.inboxItems.replaceChildren();
  if (!model.items.length) {
    elements.inboxItems.append(emptyState("Inbox is clear. Capture something when it appears."));
    return;
  }

  for (const item of model.items.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "inbox-item";

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
      button.dataset.intent = intent;
      button.textContent = label;
      actions.append(button);
    }

    const recycle = document.createElement("button");
    recycle.className = "mini-button quiet";
    recycle.type = "button";
    recycle.dataset.inboxAction = "recycle";
    recycle.dataset.itemId = item.id;
    recycle.textContent = "Recycle";
    actions.append(recycle);

    row.append(body, actions);
    elements.inboxItems.append(row);
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

elements.connectionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  try {
    settings = {
      serverUrl: elements.serverUrl.value,
      apiToken: elements.apiToken.value,
    };
    saveSettings(window.localStorage, settings);
    settings = loadSettings(window.localStorage);
    connectAndLoad();
  } catch (err) {
    setConnectionState("error", "Invalid connection settings", err.message);
  }
});

elements.resetSettings.addEventListener("click", () => {
  clearSettings(window.localStorage);
  settings = loadSettings(window.localStorage);
  applySettingsToForm();
  connectAndLoad();
});

elements.refreshDashboard.addEventListener("click", () => {
  connectAndLoad();
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
  } catch (err) {
    setConnectionState("error", "Daily focus save failed", err.message);
  } finally {
    elements.oneThingInput.disabled = false;
    elements.frogInput.disabled = false;
  }
});

elements.inboxItems.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-inbox-action]");
  if (!button) return;

  const itemId = button.dataset.itemId;
  if (!itemId) return;

  button.disabled = true;
  try {
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
  } catch (err) {
    setConnectionState("error", "Inbox action failed", err.message);
  } finally {
    button.disabled = false;
  }
});

applySettingsToForm();
connectAndLoad();
