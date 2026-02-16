const BASE_URL = "http://127.0.0.1:8000";
const HEALTH_URL = `${BASE_URL}/healthz`;
const statusEl = document.getElementById("status");
const detailEl = document.getElementById("detail");
const retryBtn = document.getElementById("retry");

let attempts = 0;
let lastError = "";
let startupTimer = null;

function scheduleRetry(delayMs) {
  if (startupTimer) clearTimeout(startupTimer);
  startupTimer = setTimeout(checkBackend, delayMs);
}

async function probeBackend() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(HEALTH_URL, {
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) {
      let detail = "";
      try {
        const payload = await response.json();
        detail = payload?.detail || payload?.status || "";
      } catch (err) {
        detail = "";
      }
      throw new Error(detail || `Health check failed (${response.status})`);
    }
    const payload = await response.json();
    if (payload?.status !== "ok") {
      throw new Error(payload?.detail || "Backend not ready");
    }
    return true;
  } finally {
    clearTimeout(timeout);
  }
}

async function checkBackend() {
  attempts += 1;
  statusEl.textContent = "Starting the local engine...";
  try {
    await probeBackend();
    statusEl.textContent = "Opening SFO...";
    detailEl.textContent = "";
    window.location.replace(BASE_URL + "/");
  } catch (err) {
    lastError = err instanceof Error ? err.message : String(err);
    detailEl.textContent = `Attempt ${attempts}: ${lastError}`;
    const delay = Math.min(1000 * 2 ** Math.min(attempts, 4), 12000);
    scheduleRetry(delay);
    if (attempts > 6) {
      retryBtn.hidden = false;
      statusEl.textContent = "SFO is taking longer than usual to start.";
      detailEl.textContent = `${detailEl.textContent} Open ${HEALTH_URL} for diagnostics.`;
    }
  }
}

retryBtn?.addEventListener("click", () => {
  if (startupTimer) clearTimeout(startupTimer);
  attempts = 0;
  retryBtn.hidden = true;
  detailEl.textContent = "";
  checkBackend();
});

checkBackend();
