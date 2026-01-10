document.addEventListener("DOMContentLoaded", () => {
  const horizon = document.querySelector(
    'select[name="time_horizon"], select[name="project_time_horizon"]'
  );
  const includeYes = document.querySelector(
    'input[name="include_this_week"][value="yes"], input[name="project_include_this_week"][value="yes"]'
  );
  const includeNo = document.querySelector(
    'input[name="include_this_week"][value="no"], input[name="project_include_this_week"][value="no"]'
  );
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

  const captureForm = document.querySelector("[data-capture-form]");
  if (captureForm) {
    const kindSelect = captureForm.querySelector("[data-capture-kind]");
    const sections = Array.from(captureForm.querySelectorAll("[data-capture-section]"));
    const titleInput = captureForm.querySelector('input[name="title"]');
    const redirectToWizard = () => {
      const raw = titleInput?.value?.trim() || "";
      const url = raw ? `/capture/wizard?prefill=${encodeURIComponent(raw)}` : "/capture/wizard";
      window.location.assign(url);
    };
    const updateCaptureSections = () => {
      const kind = kindSelect?.value || "decide_later";
      sections.forEach((section) => {
        const isActive = section.dataset.captureSection === kind;
        section.classList.toggle("hidden", !isActive);
        section.querySelectorAll("input, select, textarea").forEach((field) => {
          field.disabled = !isActive;
        });
      });
    };
    kindSelect?.addEventListener("change", () => {
      updateCaptureSections();
      if (kindSelect?.value === "not_sure") {
        redirectToWizard();
      }
    });
    updateCaptureSections();
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

  const onboardingForm = document.querySelector("[data-onboarding-wizard]");
  if (onboardingForm) {
    const steps = Array.from(onboardingForm.querySelectorAll(".wizard-step"));
    const nextBtn = onboardingForm.querySelector("[data-next]");
    const prevBtn = onboardingForm.querySelector("[data-prev]");
    const submitBtn = onboardingForm.querySelector("[data-submit]");
    let current = 0;

    const showStep = (index) => {
      steps.forEach((step, i) => step.classList.toggle("hidden", i !== index));
      prevBtn?.classList.toggle("hidden", index === 0);
      nextBtn?.classList.toggle("hidden", index === steps.length - 1);
      submitBtn?.classList.toggle("hidden", index !== steps.length - 1);
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

    showStep(0);
  }

  const tasksToggle = document.querySelector("[data-task-toggle]");
  const tasksBoard = document.querySelector("[data-task-board]");
  if (tasksToggle && tasksBoard) {
    tasksToggle.querySelectorAll("[data-view]").forEach((button) => {
      button.addEventListener("click", () => {
        const view = button.dataset.view;
        if (!view || tasksBoard.dataset.view === view) return;
        tasksBoard.dataset.view = view;
        tasksToggle
          .querySelectorAll("[data-view]")
          .forEach((btn) => btn.classList.toggle("is-active", btn.dataset.view === view));
      });
    });
  }

  const weeklyWizard = document.querySelector("[data-weekly-wizard]");
  if (weeklyWizard) {
    const steps = Array.from(weeklyWizard.querySelectorAll(".wizard-step"));
    const nextBtn = weeklyWizard.querySelector("[data-next]");
    const prevBtn = weeklyWizard.querySelector("[data-prev]");
    const submitBtn = weeklyWizard.querySelector("[data-submit]");
    let current = 0;

    const showStep = (index) => {
      steps.forEach((step, i) => step.classList.toggle("hidden", i !== index));
      prevBtn?.classList.toggle("hidden", index === 0);
      nextBtn?.classList.toggle("hidden", index === steps.length - 1);
      submitBtn?.classList.toggle("hidden", index !== steps.length - 1);
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

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest(".project-edit-toggle");
    if (!toggle) return;
    const container = toggle.closest(".project-edit");
    const form = container?.querySelector(".project-edit-form");
    if (!form) return;
    form.classList.toggle("hidden");
    if (!form.classList.contains("hidden")) {
      const input = form.querySelector('input[name="title"]');
      input?.focus();
      input?.select();
    }
  });

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest(".task-edit-toggle");
    if (!toggle) return;
    const container = toggle.closest(".task-card");
    const form = container?.querySelector(".task-edit-form");
    if (!form) return;
    form.classList.toggle("hidden");
    if (!form.classList.contains("hidden")) {
      const input = form.querySelector('input[name="verb_noun"]');
      input?.focus();
      input?.select();
    }
  });

  const horizonBoard = document.querySelector("[data-horizon-board]");
  if (horizonBoard) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
    const scrollKey = "sfo:long-range-scroll";
    const storedScroll = sessionStorage.getItem(scrollKey);
    if (storedScroll) {
      const pos = parseInt(storedScroll, 10);
      if (!Number.isNaN(pos)) {
        window.scrollTo({ top: pos, behavior: "auto" });
      }
      sessionStorage.removeItem(scrollKey);
    }

    let dragInfo = null;

    const clearDropTargets = () => {
      horizonBoard
        .querySelectorAll(".is-drop-target")
        .forEach((el) => el.classList.remove("is-drop-target"));
    };

    horizonBoard.addEventListener("dragstart", (event) => {
      const item = event.target.closest('[data-project-id][draggable="true"]');
      if (!item) return;
      const column = item.closest("[data-horizon-column]");
      if (!column) return;
      dragInfo = {
        item,
        projectId: item.dataset.projectId,
        sourceKey: column.dataset.horizonKey,
      };
      item.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", item.dataset.projectId || "");
    });

    horizonBoard.addEventListener("dragend", () => {
      if (dragInfo?.item) {
        dragInfo.item.classList.remove("is-dragging");
      }
      dragInfo = null;
      clearDropTargets();
    });

    horizonBoard.addEventListener("dragover", (event) => {
      const column = event.target.closest("[data-horizon-column]");
      if (!column) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      column.classList.add("is-drop-target");
    });

    horizonBoard.addEventListener("dragleave", (event) => {
      const column = event.target.closest("[data-horizon-column]");
      if (!column) return;
      if (!column.contains(event.relatedTarget)) {
        column.classList.remove("is-drop-target");
      }
    });

    horizonBoard.addEventListener("drop", async (event) => {
      const column = event.target.closest("[data-horizon-column]");
      if (!column || !dragInfo) return;
      event.preventDefault();
      clearDropTargets();
      const targetKey = column.dataset.horizonKey;
      if (!targetKey || targetKey === dragInfo.sourceKey) {
        dragInfo.item.classList.remove("is-dragging");
        dragInfo = null;
        return;
      }
      if (!csrfToken) {
        window.alert("Missing CSRF token. Refresh the page and try again.");
        return;
      }

      const formData = new FormData();
      formData.append("csrf_token", csrfToken);
      formData.append("time_horizon", targetKey);

      try {
        const response = await fetch(
          `/long-term/projects/${dragInfo.projectId}/horizon`,
          {
            method: "POST",
            body: formData,
            headers: { Accept: "application/json" },
            credentials: "same-origin",
          }
        );
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          window.alert(detail.detail || "Unable to update horizon. Try again.");
          return;
        }
        sessionStorage.setItem(scrollKey, String(window.scrollY || 0));
        window.location.reload();
      } catch (err) {
        window.alert("Unable to update horizon. Check your connection and try again.");
      }
    });
  }

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
    const storageKey = "sfo:coach-open";
    const clearKey = "sfo:coach-clear";
    const nudgeRoot = coachRoot.querySelector("[data-coach-nudges]");
    const modalEl = document.getElementById("app-modal");

    let context = {};
    let historyLoaded = false;
    let displacementAckHandler = null;
    let modalResolve = null;

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
        const res = await fetch("/nudges", { headers: { Accept: "application/json" } });
        if (!res.ok) return;
        const data = await res.json();
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
        "Before you add this, ask: What will you say no to so this gets protected?",
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
        const clearedAt = getClearTimestamp();
        (data.messages || []).forEach((msg) => {
          if (clearedAt && msg.created_at) {
            const ts = Date.parse(msg.created_at);
            if (!Number.isNaN(ts) && ts <= clearedAt) {
              return;
            }
          }
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

  const healthSeriesNode = document.querySelector("#health-series");
  if (healthSeriesNode) {
    let healthSeries = {};
    try {
      healthSeries = JSON.parse(healthSeriesNode.textContent || "{}");
    } catch (err) {
      healthSeries = {};
    }

    const rootStyles = getComputedStyle(document.documentElement);
    const lineColor = rootStyles.getPropertyValue("--accent-cyan").trim() || "#2da0ff";
    const dotColor = rootStyles.getPropertyValue("--success").trim() || "#49f6a3";
    const fillColor = "rgba(45, 226, 230, 0.22)";

    const chartItems = [];

    const drawChart = (container, points) => {
      const canvas = container.querySelector("canvas");
      const empty = container.querySelector(".health-chart-empty");
      if (!canvas) return;

      const values = (points || [])
        .map((point) => Number(point.value))
        .filter((val) => !Number.isNaN(val));

      if (values.length < 2) {
        if (empty) empty.style.display = "flex";
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        return;
      }

      if (empty) empty.style.display = "none";

      const width = container.clientWidth;
      const height = container.clientHeight;
      if (!width || !height) return;

      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);

      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      const padX = 10;
      const padY = 10;

      const toX = (index) =>
        padX + (index / (values.length - 1)) * (width - padX * 2);
      const toY = (val) =>
        height - padY - ((val - min) / range) * (height - padY * 2);

      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, fillColor);
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.beginPath();
      values.forEach((val, index) => {
        const x = toX(index);
        const y = toY(val);
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.lineTo(width - padX, height - padY);
      ctx.lineTo(padX, height - padY);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      ctx.beginPath();
      values.forEach((val, index) => {
        const x = toX(index);
        const y = toY(val);
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.strokeStyle = lineColor;
      ctx.lineWidth = 2;
      ctx.shadowColor = lineColor;
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.shadowBlur = 0;

      const lastIndex = values.length - 1;
      ctx.beginPath();
      ctx.fillStyle = dotColor;
      ctx.arc(toX(lastIndex), toY(values[lastIndex]), 3.5, 0, Math.PI * 2);
      ctx.fill();
    };

    document.querySelectorAll("[data-health-chart]").forEach((container) => {
      const metricId = container.dataset.metricId;
      const points = Array.isArray(healthSeries?.[metricId]) ? healthSeries[metricId] : [];
      chartItems.push({ container, points });
    });

    const renderCharts = () => {
      chartItems.forEach((item) => drawChart(item.container, item.points));
    };

    renderCharts();
    window.addEventListener("resize", () => {
      window.requestAnimationFrame(renderCharts);
    });
  }
});
