(function () {
  const defaultNoopToast = () => {};

  window.initCoachWidget = function initCoachWidget(options = {}) {
    const { showToast = defaultNoopToast, isTauriEnv = false } = options;
  const coachRoot = document.querySelector("[data-coach]");
  if (coachRoot) {
    const toggleBtn = coachRoot.querySelector("[data-coach-toggle]");
    const panel = coachRoot.querySelector("[data-coach-panel]");
    const closeBtn = coachRoot.querySelector("[data-coach-close]");
    const helpBtn = coachRoot.querySelector("[data-coach-help]");
    const clearBtn = coachRoot.querySelector("[data-coach-clear]");
    const messagesEl = coachRoot.querySelector("[data-coach-messages]");
    const quickActionsEl = coachRoot.querySelector("[data-coach-quick-actions]");
    const formEl = coachRoot.querySelector("[data-coach-form]");
    const inputEl = coachRoot.querySelector("[data-coach-input]");
    const statusEl = coachRoot.querySelector("[data-coach-status]");
    const contextEl = document.getElementById("coach-context");
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
    const coachSubmitBtn = formEl?.querySelector('button[type="submit"]');
    const storageKey = "sfo:coach-open";
    const clearKey = "sfo:coach-clear";
    const historyKey = "sfo:coach-history";
    const nudgeRoot = coachRoot.querySelector("[data-coach-nudges]");
    const modalEl = document.getElementById("app-modal");
    const coachTimeoutMs = 45000;

    let context = {};
    let historyLoaded = false;
    let historyCache = [];
    let displacementAckHandler = null;
    let modalResolve = null;
    let coachBusy = false;

    if (contextEl?.textContent) {
      try {
        context = JSON.parse(contextEl.textContent);
      } catch (err) {
        context = {};
      }
    }

    const setStatus = (text) => {
      if (statusEl) statusEl.textContent = text;
    };

    const setCoachBusy = (busy) => {
      coachBusy = busy;
      if (coachSubmitBtn) coachSubmitBtn.disabled = busy;
      if (inputEl) inputEl.setAttribute("aria-busy", busy ? "true" : "false");
    };

    const fetchJson = async (url, options = {}) => {
      const controller = new AbortController();
      const timeoutHandle = window.setTimeout(() => controller.abort(), coachTimeoutMs);
      try {
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
        });
        const raw = await response.text();
        let data = {};
        if (raw) {
          try {
            data = JSON.parse(raw);
          } catch (err) {
            data = {};
          }
        }
        return { response, data };
      } finally {
        window.clearTimeout(timeoutHandle);
      }
    };

    const persistHistory = () => {
      try {
        localStorage.setItem(historyKey, JSON.stringify(historyCache));
      } catch (err) {
        // Ignore storage errors.
      }
    };

    const recordHistory = (entry) => {
      historyCache.push(entry);
      if (historyCache.length > 200) {
        historyCache = historyCache.slice(-200);
      }
      persistHistory();
    };

    const getClearTimestamp = () => {
      try {
        const raw = localStorage.getItem(clearKey);
        if (!raw) return null;
        const parsed = Date.parse(raw);
        return Number.isNaN(parsed) ? null : parsed;
      } catch (err) {
        return null;
      }
    };

    const setClearTimestamp = () => {
      try {
        localStorage.setItem(clearKey, new Date().toISOString());
      } catch (err) {
        // Ignore storage errors.
      }
    };

    const renderHistory = (messages, { persist = true } = {}) => {
      if (!messagesEl) return;
      messagesEl.innerHTML = "";
      historyCache = [];
      let lastActions = null;
      (messages || []).forEach((msg) => {
        if (!msg || !msg.role || !msg.content) return;
        addMessage(msg.role, msg.content, { persist: false });
        const entry = {
          role: msg.role,
          content: msg.content,
          created_at: msg.created_at || new Date().toISOString(),
        };
        if (msg.actions) {
          entry.actions = msg.actions;
          lastActions = msg.actions;
        }
        historyCache.push(entry);
      });
      if (lastActions) renderQuickActions(lastActions);
      if (persist) persistHistory();
      messagesEl.scrollTop = messagesEl.scrollHeight;
    };

    const restoreCachedHistory = () => {
      if (!messagesEl) return;
      try {
        const raw = localStorage.getItem(historyKey);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return;
        const clearedAt = getClearTimestamp();
        const filtered = parsed.filter((msg) => {
          if (!clearedAt || !msg.created_at) return true;
          const ts = Date.parse(msg.created_at);
          return Number.isNaN(ts) || ts > clearedAt;
        });
        if (filtered.length) {
          renderHistory(filtered, { persist: false });
        }
      } catch (err) {
        // Ignore storage errors.
      }
    };

    const closeModal = (result) => {
      if (!modalEl) return;
      modalEl.classList.add("hidden");
      if (typeof modalResolve === "function") {
        modalResolve(result);
      }
      modalResolve = null;
    };

    const showConfirm = ({ title, body, confirmLabel = "Confirm", cancelLabel = "Cancel" }) =>
      new Promise((resolve) => {
        if (!modalEl) {
          resolve(window.confirm(body || title || "Confirm?"));
          return;
        }
        const titleEl = modalEl.querySelector(".app-modal-title");
        const bodyEl = modalEl.querySelector(".app-modal-body");
        const confirmBtn = modalEl.querySelector(".app-modal-confirm");
        const cancelBtn = modalEl.querySelector(".app-modal-cancel");
        if (titleEl) titleEl.textContent = title || "Confirm";
        if (bodyEl) bodyEl.textContent = body || "";
        if (confirmBtn) confirmBtn.textContent = confirmLabel;
        if (cancelBtn) cancelBtn.textContent = cancelLabel;
        modalResolve = resolve;
        modalEl.classList.remove("hidden");
        confirmBtn?.focus();
      });

    if (modalEl && modalEl.dataset.bound !== "1") {
      const confirmBtn = modalEl.querySelector(".app-modal-confirm");
      const cancelBtn = modalEl.querySelector(".app-modal-cancel");
      confirmBtn?.addEventListener("click", () => closeModal(true));
      cancelBtn?.addEventListener("click", () => closeModal(false));
      modalEl.addEventListener("click", (event) => {
        if (event.target === modalEl) closeModal(false);
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modalEl.classList.contains("hidden")) {
          closeModal(false);
        }
      });
      modalEl.dataset.bound = "1";
    }

    const createNudgeShell = (title, body, scope) => {
      if (!nudgeRoot) return null;
      const nudgeEl = document.createElement("div");
      nudgeEl.className = "coach-nudge";
      nudgeEl.dataset.nudgeScope = scope;

      const header = document.createElement("div");
      header.className = "coach-nudge-header";

      const from = document.createElement("span");
      from.textContent = "Charlie";

      const titleEl = document.createElement("span");
      titleEl.className = "coach-nudge-title";
      titleEl.textContent = title;

      header.appendChild(from);
      header.appendChild(titleEl);

      const bodyEl = document.createElement("div");
      bodyEl.className = "coach-nudge-body";
      bodyEl.textContent = body;

      const actionsEl = document.createElement("div");
      actionsEl.className = "coach-nudge-actions";

      nudgeEl.appendChild(header);
      nudgeEl.appendChild(bodyEl);
      nudgeEl.appendChild(actionsEl);

      return { nudgeEl, actionsEl };
    };

    const clearServerNudges = () => {
      if (!nudgeRoot) return;
      nudgeRoot
        .querySelectorAll('[data-nudge-scope="server"]')
        .forEach((node) => node.remove());
    };

    const renderServerNudge = (nudge) => {
      if (!nudgeRoot) return;
      const shell = createNudgeShell(nudge.title, nudge.body, "server");
      if (!shell) return;
      const { nudgeEl, actionsEl } = shell;
      nudgeEl.dataset.nudgeId = String(nudge.id || "");

      if (nudge.link_url) {
        const link = document.createElement("a");
        link.className = "btn ghost btn-sm";
        link.href = nudge.link_url;
        link.textContent = nudge.link_label || "Open";
        actionsEl.appendChild(link);
      }

      const snoozeSelect = document.createElement("select");
      snoozeSelect.className = "coach-nudge-select";
      [
        { label: "Snooze 10 min", value: 10 },
        { label: "Snooze 1 hour", value: 60 },
        { label: "Snooze 6 hours", value: 360 },
        { label: "Snooze 1 day", value: 1440 },
      ].forEach((opt) => {
        const option = document.createElement("option");
        option.value = String(opt.value);
        option.textContent = opt.label;
        snoozeSelect.appendChild(option);
      });
      actionsEl.appendChild(snoozeSelect);

      const snoozeBtn = document.createElement("button");
      snoozeBtn.type = "button";
      snoozeBtn.className = "btn ghost btn-sm";
      snoozeBtn.textContent = "Snooze";
      snoozeBtn.addEventListener("click", async () => {
        if (!csrfToken) return;
        snoozeBtn.disabled = true;
        const minutes = parseInt(snoozeSelect.value || "10", 10);
        try {
          const res = await fetch(`/nudges/${nudge.id}/snooze`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "x-csrf-token": csrfToken || "",
              Accept: "application/json",
            },
            body: JSON.stringify({ minutes }),
          });
          if (!res.ok) return;
          nudgeEl.remove();
        } catch (err) {
          // Ignore errors; the nudge will remain.
        } finally {
          snoozeBtn.disabled = false;
        }
      });
      actionsEl.appendChild(snoozeBtn);

      const doneBtn = document.createElement("button");
      doneBtn.type = "button";
      doneBtn.className = "btn ghost btn-sm";
      doneBtn.textContent = "Mark done";
      doneBtn.addEventListener("click", async () => {
        if (!csrfToken) return;
        doneBtn.disabled = true;
        try {
          const res = await fetch(`/nudges/${nudge.id}/complete`, {
            method: "POST",
            headers: { "x-csrf-token": csrfToken || "", Accept: "application/json" },
          });
          if (!res.ok) return;
          nudgeEl.remove();
        } catch (err) {
          // Ignore errors; the nudge will remain.
        } finally {
          doneBtn.disabled = false;
        }
      });
      actionsEl.appendChild(doneBtn);

      nudgeRoot.appendChild(nudgeEl);
    };

    const loadNudges = async () => {
      if (!nudgeRoot) return;
      try {
        let data = null;
        if (csrfToken) {
          const refreshRes = await fetch("/nudges/refresh", {
            method: "POST",
            headers: {
              "x-csrf-token": csrfToken || "",
              Accept: "application/json",
            },
          });
          if (refreshRes.ok) {
            data = await refreshRes.json();
          }
        }
        if (!data) {
          const res = await fetch("/nudges", { headers: { Accept: "application/json" } });
          if (!res.ok) return;
          data = await res.json();
        }
        clearServerNudges();
        (data.nudges || []).forEach(renderServerNudge);
      } catch (err) {
        // Ignore nudge load failures.
      }
    };

    const hideDisplacementNudge = () => {
      if (!nudgeRoot) return;
      const existing = nudgeRoot.querySelector('[data-nudge-scope="displacement"]');
      existing?.remove();
      displacementAckHandler = null;
    };

    const showDisplacementNudge = (onAcknowledge) => {
      if (!nudgeRoot) return;
      displacementAckHandler = onAcknowledge;
      const existing = nudgeRoot.querySelector('[data-nudge-scope="displacement"]');
      if (existing) return;
      const shell = createNudgeShell(
        "Displacement check",
        "Before you add this, ask: What will you say no to so this gets protected? Click \"I considered this\" to continue saving.",
        "displacement"
      );
      if (!shell) return;
      const { nudgeEl, actionsEl } = shell;
      const ackBtn = document.createElement("button");
      ackBtn.type = "button";
      ackBtn.className = "btn ghost btn-sm";
      ackBtn.textContent = "I considered this";
      ackBtn.addEventListener("click", async () => {
        if (typeof displacementAckHandler === "function") {
          await displacementAckHandler();
        }
        hideDisplacementNudge();
      });
      actionsEl.appendChild(ackBtn);
      nudgeRoot.prepend(nudgeEl);
    };

    const acknowledgeDisplacement = async (kind, title) => {
      if (!csrfToken) return;
      try {
        await fetch("/nudges/displacement/ack", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-csrf-token": csrfToken || "",
          },
          body: JSON.stringify({ capture_kind: kind, title }),
        });
      } catch (err) {
        // Ignore logging errors.
      }
    };

    const initDisplacementGuard = ({ form, getKind, getTitle, bindKindChange, autoShow }) => {
      if (!form || !nudgeRoot) return;
      const ackInput = form.querySelector("[data-displacement-ack]");
      if (!ackInput) return;

      const needsAck = () => {
        const kind = getKind?.();
        return kind === "task" || kind === "project";
      };

      const sync = () => {
        if (!needsAck()) {
          ackInput.value = "0";
          hideDisplacementNudge();
          return;
        }
        if (ackInput.value === "1") {
          hideDisplacementNudge();
          return;
        }
        showDisplacementNudge(async () => {
          ackInput.value = "1";
          await acknowledgeDisplacement(getKind?.(), getTitle?.());
        });
      };

      form.addEventListener("submit", (event) => {
        if (!needsAck()) return;
        if (ackInput.value === "1") return;
        event.preventDefault();
        sync();
      });

      if (bindKindChange) {
        bindKindChange(sync);
      }

      if (autoShow) {
        sync();
      }
    };

    const setOpenState = (isOpen) => {
      try {
        sessionStorage.setItem(storageKey, isOpen ? "1" : "0");
      } catch (err) {
        // Ignore storage errors (e.g., private mode).
      }
    };

    const getOpenState = () => {
      try {
        return sessionStorage.getItem(storageKey) === "1";
      } catch (err) {
        return false;
      }
    };

    const addMessage = (role, content, { persist = true, actions = null, createdAt = null } = {}) => {
      if (!messagesEl) return null;
      const messageEl = document.createElement("div");
      messageEl.className = `coach-message coach-message--${role}`;
      messageEl.textContent = content;
      messagesEl.appendChild(messageEl);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      if (persist) {
        recordHistory({
          role,
          content,
          actions: actions || null,
          created_at: createdAt || new Date().toISOString(),
        });
      }
      return messageEl;
    };

    const renderQuickActions = (actions) => {
      if (!quickActionsEl) return;
      quickActionsEl.innerHTML = "";
      if (!actions || !actions.length) return;
      actions.forEach((action) => {
        if (!action?.url || !action?.label) return;
        const link = document.createElement("a");
        link.href = action.url;
        link.className = "btn ghost btn-sm coach-action-btn";
        link.textContent = action.label;
        quickActionsEl.appendChild(link);
      });
    };

    restoreCachedHistory();

    const loadHistory = async () => {
      if (historyLoaded) return;
      historyLoaded = true;
      setStatus("Loading history...");
      try {
        const res = await fetch("/coach/history");
        if (!res.ok) throw new Error("Failed history");
        const data = await res.json();
        const clearedAt = getClearTimestamp();
        const filtered = (data.messages || []).filter((msg) => {
          if (!clearedAt || !msg.created_at) return true;
          const ts = Date.parse(msg.created_at);
          return Number.isNaN(ts) || ts > clearedAt;
        });
        if (!filtered.length && historyCache.length) {
          setStatus("Ready");
          return;
        }
        renderHistory(filtered);
        setStatus("Ready");
      } catch (err) {
        setStatus("History unavailable");
      }
    };

    const coachEscapeHtml = (value) =>
      `${value || ""}`.replace(/[&<>"']/g, (ch) => {
        switch (ch) {
          case "&":
            return "&amp;";
          case "<":
            return "&lt;";
          case ">":
            return "&gt;";
          case '"':
            return "&quot;";
          case "'":
            return "&#39;";
          default:
            return ch;
        }
      });

    const parseTimeToMinutes = (value) => {
      if (!value) return null;
      const parts = `${value}`.split(":");
      if (parts.length < 2) return null;
      const hour = Number.parseInt(parts[0], 10);
      const minute = Number.parseInt(parts[1], 10);
      if (Number.isNaN(hour) || Number.isNaN(minute)) return null;
      return hour * 60 + minute;
    };

    const formatTimeLabel = (value) => {
      const total = parseTimeToMinutes(value);
      if (total === null) return "";
      const hour24 = Math.floor(total / 60) % 24;
      const minute = total % 60;
      const ampm = hour24 >= 12 ? "PM" : "AM";
      const hour12 = hour24 % 12 || 12;
      return `${hour12}:${String(minute).padStart(2, "0")} ${ampm}`;
    };

    const syncListHtml = (doc, selector) => {
      const current = document.querySelector(selector);
      const next = doc.querySelector(selector);
      if (!current || !next) return false;
      current.innerHTML = next.innerHTML;
      current.querySelectorAll(".list-item").forEach((item) => {
        if (isTauriEnv) {
          item.removeAttribute("draggable");
        } else {
          item.setAttribute("draggable", "true");
        }
      });
      return true;
    };

    const refreshHomePanelsInline = async () => {
      if (window.location.pathname !== "/") return false;
      try {
        const response = await fetch("/", {
          headers: { Accept: "text/html", "x-requested-with": "fetch" },
          credentials: "same-origin",
        });
        if (!response.ok) return false;
        const html = await response.text();
        const doc = new DOMParser().parseFromString(html, "text/html");

        const currentInboxCount = document.querySelector(".inbox-count");
        const nextInboxCount = doc.querySelector(".inbox-count");
        if (currentInboxCount && nextInboxCount) {
          currentInboxCount.textContent = nextInboxCount.textContent;
        }

        syncListHtml(doc, "[data-home-inbox-list]");
        syncListHtml(doc, "[data-home-today-list]");

        const currentNowPanel = document.querySelector("[data-home-now-panel]");
        const nextNowPanel = doc.querySelector("[data-home-now-panel]");
        if (currentNowPanel && nextNowPanel) {
          currentNowPanel.innerHTML = nextNowPanel.innerHTML;
        }

        const currentNowText = document.querySelector("[data-now-text]");
        const nextNowText = doc.querySelector("[data-now-text]");
        if (currentNowText && nextNowText) {
          currentNowText.textContent = nextNowText.textContent;
        }

        const nextContext = doc.getElementById("coach-context");
        if (nextContext?.textContent) {
          try {
            context = JSON.parse(nextContext.textContent);
          } catch (err) {
            // Keep prior context if parsing fails.
          }
        }
        return true;
      } catch (err) {
        return false;
      }
    };

    const refreshTasksPanelsInline = async () => {
      if (!window.location.pathname.startsWith("/tasks")) return false;
      try {
        const response = await fetch(window.location.pathname, {
          headers: { Accept: "text/html", "x-requested-with": "fetch" },
          credentials: "same-origin",
        });
        if (!response.ok) return false;
        const html = await response.text();
        const doc = new DOMParser().parseFromString(html, "text/html");
        let applied = false;

        const currentPageNav = document.querySelector(".tasks-page-nav");
        const nextPageNav = doc.querySelector(".tasks-page-nav");
        if (currentPageNav && nextPageNav) {
          currentPageNav.innerHTML = nextPageNav.innerHTML;
          applied = true;
        }

        const currentViewNav = document.querySelector(".tasks-view-nav");
        const nextViewNav = doc.querySelector(".tasks-view-nav");
        if (currentViewNav && nextViewNav) {
          currentViewNav.innerHTML = nextViewNav.innerHTML;
          applied = true;
        }

        const currentBoard = document.querySelector(".tasks-board");
        const nextBoard = doc.querySelector(".tasks-board");
        if (currentBoard && nextBoard) {
          currentBoard.dataset.view = nextBoard.dataset.view || currentBoard.dataset.view || "time";
          currentBoard.innerHTML = nextBoard.innerHTML;
          currentBoard.querySelectorAll("[data-task-card]").forEach((card) => {
            if (isTauriEnv) {
              card.removeAttribute("draggable");
            } else {
              card.setAttribute("draggable", "true");
            }
          });
          applied = true;
        } else {
          const currentShell = document.querySelector(".tasks-shell");
          const nextShell = doc.querySelector(".tasks-shell");
          if (currentShell && nextShell) {
            currentShell.innerHTML = nextShell.innerHTML;
            applied = true;
          }
        }

        const nextContext = doc.getElementById("coach-context");
        if (nextContext?.textContent) {
          try {
            context = JSON.parse(nextContext.textContent);
          } catch (err) {
            // Keep prior context if parsing fails.
          }
        }
        return applied;
      } catch (err) {
        return false;
      }
    };

    const addCoachBlockToCalendar = (effectBlock) => {
      if (window.location.pathname !== "/") return false;
      if (!effectBlock || !effectBlock.id || !effectBlock.date) return false;
      const eventsEl = document.querySelector("[data-home-calendar-events]");
      if (!eventsEl) return false;
      if (eventsEl.querySelector(`[data-block-id="${effectBlock.id}"]`)) return true;

      const todayIso = new Date().toISOString().slice(0, 10);
      if (effectBlock.date !== todayIso) return false;

      const nowLineEl = document.querySelector("[data-now-line]");
      const dayStart = Number.parseInt(nowLineEl?.dataset.startMinutes || "360", 10);
      const dayTotal = Number.parseInt(nowLineEl?.dataset.totalMinutes || "1020", 10);
      const dayEnd = dayStart + dayTotal;

      const startMin = parseTimeToMinutes(effectBlock.start_time);
      const endMin = parseTimeToMinutes(effectBlock.end_time);
      if (startMin === null || endMin === null || endMin <= startMin) return false;

      const effectiveStart = Math.max(dayStart, startMin);
      const effectiveEnd = Math.min(dayEnd, endMin);
      if (effectiveEnd <= dayStart || effectiveStart >= dayEnd) return false;

      const topPct = Math.max(0, ((effectiveStart - dayStart) / dayTotal) * 100);
      const heightPct = Math.max(5, ((effectiveEnd - effectiveStart) / dayTotal) * 100);
      const blockType = `${effectBlock.block_type || "focus"}`.toLowerCase();
      const title = effectBlock.title || `${blockType.charAt(0).toUpperCase()}${blockType.slice(1)} block`;
      const startLabel = formatTimeLabel(effectBlock.start_time);
      const endLabel = formatTimeLabel(effectBlock.end_time);

      const blockEl = document.createElement("div");
      blockEl.className = `event-block ${blockType}`;
      blockEl.dataset.blockId = String(effectBlock.id);
      blockEl.style.top = `${topPct}%`;
      blockEl.style.height = `${heightPct}%`;
      blockEl.innerHTML = `
        <div class="event-top">
          <div class="event-time">${coachEscapeHtml(startLabel)}${endLabel ? ` - ${coachEscapeHtml(endLabel)}` : ""}</div>
        </div>
        <div class="event-label">${coachEscapeHtml(title)}</div>
      `;
      eventsEl.appendChild(blockEl);
      return true;
    };

    const applyOneThingInline = (oneThing) => {
      const title = `${oneThing || ""}`.trim();
      if (!title) return false;
      let applied = false;

      const nowText = document.querySelector("[data-now-text]");
      if (nowText) {
        nowText.textContent = title;
        applied = true;
      }

      const oneThingCard = document.querySelector("[data-home-one-thing-card]");
      const oneThingRow = document.querySelector("[data-home-one-thing-row]");
      const oneThingText = document.querySelector("[data-home-one-thing-text]");
      if (oneThingCard && oneThingRow && oneThingText) {
        oneThingCard.classList.remove("hidden");
        oneThingRow.classList.remove("hidden");
        oneThingText.textContent = title;
        applied = true;
      }

      const noBlockCopy = document.querySelector("[data-home-no-block-copy]");
      if (noBlockCopy) {
        noBlockCopy.textContent =
          "No block active right now. One Thing is set. Pick a Frog and protect a block.";
        applied = true;
      }

      return applied;
    };

    const applyCoachEffects = async (effects) => {
      if (!effects?.refresh) return false;
      let applied = false;
      const screenId = context?.screen?.id || "";
      if (effects.type === "one_thing_updated" && effects.one_thing) {
        const updatedOneThing = applyOneThingInline(effects.one_thing);
        applied = updatedOneThing || applied;
      }
      if (screenId === "home" || window.location.pathname === "/") {
        const refreshed = await refreshHomePanelsInline();
        applied = refreshed || applied;
      }
      if (
        (screenId === "tasks" || window.location.pathname.startsWith("/tasks")) &&
        effects.type === "task_created"
      ) {
        const refreshedTasks = await refreshTasksPanelsInline();
        applied = refreshedTasks || applied;
      }
      if (effects.type === "block_created" && effects.block) {
        const inserted = addCoachBlockToCalendar(effects.block);
        applied = inserted || applied;
      }
      return applied;
    };

    const sendMessage = async (text) => {
      const message = (text || "").trim();
      if (!message) return;
      if (coachBusy) {
        showToast("Charlie is still replying. Please wait a moment.", {
          variant: "error",
          timeout: 2600,
        });
        return;
      }
      addMessage("user", message);
      if (inputEl) inputEl.value = "";
      setCoachBusy(true);
      setStatus("Thinking...");
      const pending = addMessage("assistant", "Thinking...", { persist: false });
      try {
        const { response, data } = await fetchJson("/coach/message", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-csrf-token": csrfToken || "",
          },
          body: JSON.stringify({ message, screen_context: context }),
        });
        if (!response.ok) {
          throw new Error(data.detail || `Coach error (${response.status})`);
        }
        const replyText = data.reply || "No response yet.";
        if (pending) pending.textContent = replyText;
        recordHistory({
          role: "assistant",
          content: replyText,
          actions: data.actions || null,
          created_at: new Date().toISOString(),
        });
        renderQuickActions(data.actions);
        const engineLabel =
          data.engine === "ollama"
            ? "Local LLM"
            : data.engine === "action"
              ? "Updated"
              : "Coach-lite";
        setStatus(engineLabel);
        if (data.effects?.refresh) {
          const appliedInline = await applyCoachEffects(data.effects);
          showToast(
            appliedInline
              ? "Saved and updated."
              : "Saved. Refresh when you want to see updated panels.",
            { variant: "success", timeout: 3200 }
          );
        }
      } catch (err) {
        const timeout = err?.name === "AbortError";
        if (pending) {
          pending.textContent = timeout
            ? "Charlie took too long to respond. Please try again."
            : "Couldn't reach Charlie just now. Try again.";
        }
        setStatus(timeout ? "Timed out" : "Offline");
        showToast(
          timeout
            ? "Charlie timed out. Your request was not lost, but please retry."
            : "Coach request failed. Check connection and try again.",
          { variant: "error", timeout: 3400 }
        );
      } finally {
        setCoachBusy(false);
      }
    };

    const openPanel = ({ focusInput = false } = {}) => {
      if (!panel) return;
      panel.classList.remove("hidden");
      toggleBtn?.setAttribute("aria-expanded", "true");
      coachRoot.classList.add("is-open");
      loadHistory();
      if (focusInput) inputEl?.focus();
      setOpenState(true);
    };

    const closePanel = () => {
      if (!panel) return;
      panel.classList.add("hidden");
      toggleBtn?.setAttribute("aria-expanded", "false");
      coachRoot.classList.remove("is-open");
      setOpenState(false);
    };

    toggleBtn?.addEventListener("click", () => {
      if (!panel) return;
      if (panel.classList.contains("hidden")) {
        openPanel({ focusInput: true });
      } else {
        closePanel();
      }
    });

    closeBtn?.addEventListener("click", () => {
      closePanel();
    });

    helpBtn?.addEventListener("click", () => {
      sendMessage("Help me with what I'm looking at.");
    });

    clearBtn?.addEventListener("click", async () => {
      const confirmed = await showConfirm({
        title: "Clear this chat view?",
        body: "History stays in memory.",
        confirmLabel: "Clear",
        cancelLabel: "Keep",
      });
      if (!confirmed) return;
      setClearTimestamp();
      if (messagesEl) messagesEl.innerHTML = "";
      if (quickActionsEl) quickActionsEl.innerHTML = "";
      historyCache = [];
      try {
        localStorage.removeItem(historyKey);
      } catch (err) {
        // Ignore storage errors.
      }
      historyLoaded = true;
      setStatus("Ready");
    });

    formEl?.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(inputEl?.value || "");
    });

    if (panel && getOpenState()) {
      openPanel({ focusInput: false });
    } else {
      toggleBtn?.setAttribute("aria-expanded", panel?.classList.contains("hidden") ? "false" : "true");
    }

    loadNudges();

    const captureForm = document.querySelector("[data-capture-form]");
    if (captureForm) {
      const kindSelect = captureForm.querySelector("[data-capture-kind]");
      const titleInput = captureForm.querySelector('input[name="title"]');
      initDisplacementGuard({
        form: captureForm,
        getKind: () => kindSelect?.value,
        getTitle: () => titleInput?.value,
        bindKindChange: (handler) => kindSelect?.addEventListener("change", handler),
        autoShow: true,
      });
    }

    const wizardForm = document.querySelector("#wizardForm");
    if (wizardForm) {
      const kindInputs = wizardForm.querySelectorAll('input[name="item_kind"]');
      const titleInput = wizardForm.querySelector('input[name="capture_text"]');
      initDisplacementGuard({
        form: wizardForm,
        getKind: () =>
          wizardForm.querySelector('input[name="item_kind"]:checked')?.value,
        getTitle: () => titleInput?.value,
        bindKindChange: (handler) =>
          kindInputs.forEach((input) => input.addEventListener("change", handler)),
        autoShow: false,
      });
    }
  }

  };
})();
