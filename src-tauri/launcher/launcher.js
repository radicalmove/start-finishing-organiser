import {
  buildBootstrapViewModel,
  clearSettings,
  loadSettings,
  requestJson,
  saveSettings,
} from "./client.js";

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
  nowTitle: document.getElementById("now-title"),
  nowMeta: document.getElementById("now-meta"),
  nextBlock: document.getElementById("next-block"),
  inboxTotal: document.getElementById("inbox-total"),
  inboxCounts: document.getElementById("inbox-counts"),
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

    const summary = await requestJson(window.fetch.bind(window), settings, "/api/v1/bootstrap");
    renderDashboard(buildBootstrapViewModel(summary));
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
  renderItems(elements.todayTasks, model.todayTasks, "No Today tasks yet.");
  renderItems(elements.weeklyProjects, model.weeklyProjects, "No weekly projects selected.");
  renderBlocks(elements.todayBlocks, model.todayBlocks);
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

applySettingsToForm();
connectAndLoad();
