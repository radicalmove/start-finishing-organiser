document.addEventListener("DOMContentLoaded", () => {
  const horizon = document.querySelector('select[name="time_horizon"]');
  const includeYes = document.querySelector('input[name="include_this_week"][value="yes"]');
  const includeNo = document.querySelector('input[name="include_this_week"][value="no"]');
  const helper = document.querySelector("[data-week-helper]");

  const updateHelper = () => {
    if (!horizon || !includeYes || !includeNo || !helper) return;
    const value = horizon.value;
    const isWeek = value === "week";

    helper.classList.toggle("hidden", isWeek);
    if (isWeek) {
      includeYes.checked = true;
    } else {
      includeNo.checked = true;
    }
  };

  if (horizon) {
    horizon.addEventListener("change", updateHelper);
    updateHelper();
  }

  // Wizard navigation
  const form = document.querySelector("#wizardForm");
  if (form) {
    const steps = Array.from(form.querySelectorAll(".wizard-step"));
    const nextBtn = form.querySelector("[data-next]");
    const prevBtn = form.querySelector("[data-prev]");
    const submitBtn = form.querySelector("[data-submit]");
    const attachProject = form.querySelector("[data-attach-project]");
    const projectCategory = form.querySelector("[data-project-category]");
    const horizonSelect = form.querySelector('select[name="horizon"]');
    const includeRadios = form.querySelectorAll('input[name="include_this_week"]');
    const helperNote = form.querySelector(".note.helper");

    let current = 0;

    const waitingField = form.querySelector("[data-waiting-person]");

    const showStep = (index) => {
      steps.forEach((s, i) => s.classList.toggle("hidden", i !== index));
      prevBtn.classList.toggle("hidden", index === 0);
      nextBtn.classList.toggle("hidden", index === steps.length - 1);
      submitBtn.classList.toggle("hidden", index !== steps.length - 1);
    };

    const syncKind = () => {
      const kind = form.querySelector('input[name="item_kind"]:checked')?.value;
      const owner = form.querySelector('input[name="owner_type"]:checked')?.value;
      if (!attachProject || !projectCategory) return;
      if (kind === "task") {
        attachProject.classList.remove("hidden");
        projectCategory.classList.add("hidden");
      } else {
        attachProject.classList.add("hidden");
        projectCategory.classList.remove("hidden");
      }
      if (waitingField) {
        waitingField.classList.toggle("hidden", owner !== "opp");
      }
    };

    const syncHorizon = () => {
      if (!horizonSelect || !helperNote || !includeRadios.length) return;
      const val = horizonSelect.value;
      const isWeek = val === "week" || val === "today";
      helperNote.classList.toggle("hidden", isWeek);
      includeRadios.forEach((r) => {
        if (isWeek && r.value === "yes") r.checked = true;
        if (!isWeek && r.value === "no") r.checked = true;
      });
    };

    nextBtn?.addEventListener("click", () => {
      if (current < steps.length - 1) {
        current += 1;
        showStep(current);
      }
    });
    prevBtn?.addEventListener("click", () => {
      if (current > 0) {
        current -= 1;
        showStep(current);
      }
    });

    form.querySelectorAll('input[name="item_kind"]').forEach((r) =>
      r.addEventListener("change", syncKind)
    );
    form.querySelectorAll('input[name="owner_type"]').forEach((r) =>
      r.addEventListener("change", syncKind)
    );
    horizonSelect?.addEventListener("change", syncHorizon);

    syncKind();
    syncHorizon();
    showStep(0);
  }

  // Digital clock
  const clockTime = document.querySelector("#clock-time");
  const clockDate = document.querySelector("#clock-date");
  const nowLine = document.querySelector("[data-now-line]");

  const updateClock = () => {
    // Digital clock (header) + dynamic now-line on the calendar
    const now = new Date();
    let hours = now.getHours();
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    const minutes = String(now.getMinutes()).padStart(2, "0");
    if (clockTime) clockTime.textContent = `${hours}:${minutes} ${ampm}`;
    if (clockDate) {
      const options = { weekday: "long", year: "numeric", month: "long", day: "numeric" };
      clockDate.textContent = now.toLocaleDateString(undefined, options);
    }

    if (nowLine) {
      // Reposition the pink line once per second; data attrs come from the backend
      const start = parseInt(nowLine.dataset.startMinutes || "360", 10);
      const total = parseInt(nowLine.dataset.totalMinutes || "960", 10);
      const minutesNow = now.getHours() * 60 + now.getMinutes();
      const rel = ((minutesNow - start) / total) * 100;
      const clamped = Math.max(0, Math.min(100, rel));
      nowLine.style.top = `${clamped}%`;
      const label = nowLine.querySelector(".now-line-label");
      if (label) {
        label.textContent = `${hours}:${minutes} ${ampm}`;
      }
      nowLine.style.display = minutesNow >= start && minutesNow <= start + total ? "block" : "none";
    }
  };
  updateClock();
  setInterval(updateClock, 1000);

  // Auto-refresh calendar views every minute to pick up new events (avoid disrupting forms).
  const hasCalendar = document.querySelector(".calendar-panel, .week-calendar-panel");
  if (hasCalendar) {
    setInterval(() => {
      window.location.reload();
    }, 60 * 1000);
  }

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest(".event-edit-toggle");
    if (!toggle) return;
    const container = toggle.closest(".event-edit");
    const form = container?.querySelector(".event-edit-form");
    if (!form) return;
    form.classList.toggle("hidden");
    if (!form.classList.contains("hidden")) {
      const input = form.querySelector('input[name="title"]');
      input?.focus();
      input?.select();
    }
  });

  const coachRoot = document.querySelector("[data-coach]");
  if (coachRoot) {
    const toggleBtn = coachRoot.querySelector("[data-coach-toggle]");
    const panel = coachRoot.querySelector("[data-coach-panel]");
    const closeBtn = coachRoot.querySelector("[data-coach-close]");
    const helpBtn = coachRoot.querySelector("[data-coach-help]");
    const messagesEl = coachRoot.querySelector("[data-coach-messages]");
    const quickActionsEl = coachRoot.querySelector("[data-coach-quick-actions]");
    const formEl = coachRoot.querySelector("[data-coach-form]");
    const inputEl = coachRoot.querySelector("[data-coach-input]");
    const statusEl = coachRoot.querySelector("[data-coach-status]");
    const contextEl = document.getElementById("coach-context");
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");

    let context = {};
    let historyLoaded = false;

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

    const addMessage = (role, content) => {
      if (!messagesEl) return null;
      const messageEl = document.createElement("div");
      messageEl.className = `coach-message coach-message--${role}`;
      messageEl.textContent = content;
      messagesEl.appendChild(messageEl);
      messagesEl.scrollTop = messagesEl.scrollHeight;
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

    const loadHistory = async () => {
      if (historyLoaded) return;
      historyLoaded = true;
      setStatus("Loading history...");
      try {
        const res = await fetch("/coach/history");
        if (!res.ok) throw new Error("Failed history");
        const data = await res.json();
        (data.messages || []).forEach((msg) => {
          addMessage(msg.role, msg.content);
          if (msg.actions) {
            renderQuickActions(msg.actions);
          }
        });
        setStatus("Ready");
      } catch (err) {
        setStatus("History unavailable");
      }
    };

    const sendMessage = async (text) => {
      const message = (text || "").trim();
      if (!message) return;
      addMessage("user", message);
      if (inputEl) inputEl.value = "";
      setStatus("Thinking...");
      const pending = addMessage("assistant", "Thinking...");
      try {
        const res = await fetch("/coach/message", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-csrf-token": csrfToken || "",
          },
          body: JSON.stringify({ message, screen_context: context }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Coach error");
        if (pending) pending.textContent = data.reply || "No response yet.";
        renderQuickActions(data.actions);
        setStatus(data.engine === "ollama" ? "Local LLM" : "Coach-lite");
      } catch (err) {
        if (pending) pending.textContent = "Couldn't reach Charlie just now. Try again.";
        setStatus("Offline");
      }
    };

    toggleBtn?.addEventListener("click", () => {
      panel?.classList.toggle("hidden");
      if (panel && !panel.classList.contains("hidden")) {
        loadHistory();
        inputEl?.focus();
      }
    });

    closeBtn?.addEventListener("click", () => {
      panel?.classList.add("hidden");
    });

    helpBtn?.addEventListener("click", () => {
      sendMessage("Help me with what I'm looking at.");
    });

    formEl?.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(inputEl?.value || "");
    });
  }
});
