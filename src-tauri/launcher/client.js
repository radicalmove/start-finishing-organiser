export const DEFAULT_SERVER_URL = "http://127.0.0.1:8088";

const SERVER_URL_KEY = "sfo.rust.serverUrl";
const API_TOKEN_KEY = "sfo.rust.apiToken";
const PERSONAL_PROJECT_PATTERN =
  /\b(appointment|optometrist|doctor|dentist|health|family|home|house|kid|kids|school|holiday|trip|birthday|personal|exercise|training|winter family)\b/i;

export const WORKFLOWS = [
  { id: "today", label: "Today" },
  { id: "capture", label: "Capture" },
  { id: "process", label: "Process" },
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

export function buildBootstrapViewModel(summary) {
  const inbox = summary?.inbox || {};
  const weeklyProjects = (summary?.weekly_projects || []).map((project) => ({
    title: project.title || "Untitled project",
    meta: compactJoin([project.category, project.time_horizon]),
  }));
  const todayTasks = (summary?.today_tasks || []).map((task) => ({
    title: task.verb_noun || "Untitled task",
    description: task.description || "No notes yet.",
    meta: compactJoin([
      task.block_type,
      task.frog ? "Frog" : "",
      task.alignment,
    ]),
  }));
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
    todayLabel: summary?.today || "Today",
    currentTime: trimSeconds(summary?.current_time || ""),
    inbox,
    inboxTotal:
      Number(inbox.unprocessed || 0) +
      Number(inbox.learn_explore || 0) +
      Number(inbox.enjoy_recover || 0) +
      Number(inbox.park_let_go || 0) +
      Number(inbox.recycle_bin || 0),
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
    queue: base.items.slice(0, 6),
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

function setOptional(target, key, value) {
  const text = optionalText(value);
  if (text) {
    target[key] = text;
  }
}

function positiveInteger(value) {
  const number = Number.parseInt(String(value || ""), 10);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function trimSeconds(value) {
  return String(value || "").replace(/^(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?$/, "$1");
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
