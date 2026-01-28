const BASE_URL = "http://127.0.0.1:8000";
const HEALTH_URL = `${BASE_URL}/healthz`;
const statusEl = document.getElementById("status");
const detailEl = document.getElementById("detail");
const retryBtn = document.getElementById("retry");

let attempts = 0;
let lastError = "";

async function checkBackend() {
  attempts += 1;
  statusEl.textContent = "Starting the local engine...";
  try {
    await fetch(HEALTH_URL, { cache: "no-store", mode: "no-cors" });
    statusEl.textContent = "Opening SFO...";
    window.location.replace(BASE_URL + "/");
  } catch (err) {
    lastError = err instanceof Error ? err.message : String(err);
    detailEl.textContent = `Attempt ${attempts}: ${lastError}`;
    const delay = Math.min(2000 + attempts * 400, 6000);
    setTimeout(checkBackend, delay);
    if (attempts > 6) {
      retryBtn.hidden = false;
      statusEl.textContent = "SFO is taking longer than usual to start.";
    }
  }
}

retryBtn?.addEventListener("click", () => {
  attempts = 0;
  retryBtn.hidden = true;
  detailEl.textContent = "";
  checkBackend();
});

checkBackend();
