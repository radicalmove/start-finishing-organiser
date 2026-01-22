document.addEventListener("DOMContentLoaded", () => {
  let openGuidedCaptureModal = null;
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
      if (typeof openGuidedCaptureModal === "function") {
        openGuidedCaptureModal({ prefill: raw });
        return;
      }
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
    const projectColor = form.querySelector("[data-project-color]");
    const horizonSelect = form.querySelector('select[name="horizon"]');
    const includeRadios = form.querySelectorAll('input[name="include_this_week"]');
    const includeWeekFields = form.querySelectorAll("[data-include-week]");
    const helperNote = form.querySelector(".note.helper");
    const horizonLabel = form.querySelector("[data-horizon-label]");
    const horizonNoteTask = form.querySelector("[data-horizon-note-task]");
    const horizonNoteProject = form.querySelector("[data-horizon-note-project]");
    const blockStep = form.querySelector('.wizard-step[data-step="5"]');
    const notSureSteps = Array.from(form.querySelectorAll("[data-not-sure-step]"));
    const notSureDecisionInputs = Array.from(
      form.querySelectorAll('input[name="not_sure_decision"]')
    );
    const notSureDetails = form.querySelector('textarea[name="not_sure_details"]');
    const notSureSuggestBtn = form.querySelector("[data-not-sure-suggest]");
    const notSureStatus = form.querySelector("[data-not-sure-status]");
    const notSureSuggestion = form.querySelector("[data-not-sure-suggestion]");
    const notSureSuggestionKind = form.querySelector("[data-not-sure-suggestion-kind]");
    const notSureSuggestionText = form.querySelector("[data-not-sure-suggestion-text]");
    const notSureUseBtn = form.querySelector("[data-not-sure-use]");
    const horizonStep = form.querySelector('.wizard-step[data-step="3"]');
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");

    let current = 0;
    let currentKind = "task";

    const waitingField = form.querySelector("[data-waiting-person]");

    const getActiveSteps = () =>
      steps.filter((step) => step.dataset.stepDisabled !== "true");

    const showStep = (index) => {
      const activeSteps = getActiveSteps();
      const clamped = Math.max(0, Math.min(index, activeSteps.length - 1));
      activeSteps.forEach((s, i) => s.classList.toggle("hidden", i !== clamped));
      steps.forEach((step) => {
        if (step.dataset.stepDisabled === "true") {
          step.classList.add("hidden");
        }
      });
      prevBtn.classList.toggle("hidden", clamped === 0);
      nextBtn.classList.toggle("hidden", clamped >= activeSteps.length - 1);
      submitBtn.classList.toggle("hidden", clamped < activeSteps.length - 1);
      current = clamped;
    };

    const setSectionActive = (section, isActive) => {
      if (!section) return;
      section.classList.toggle("hidden", !isActive);
      section
        .querySelectorAll("input, select, textarea")
        .forEach((field) => (field.disabled = !isActive));
    };

    const setStepEnabled = (step, isEnabled) => {
      if (!step) return;
      step.dataset.stepDisabled = isEnabled ? "false" : "true";
      if (!isEnabled) {
        step.classList.add("hidden");
      }
      step
        .querySelectorAll("input, select, textarea, button")
        .forEach((field) => {
          if (!isEnabled) {
            if (!field.disabled) {
              field.dataset.stepDisabled = "true";
            }
            field.disabled = true;
            return;
          }
          if (field.dataset.stepDisabled === "true") {
            field.disabled = false;
            delete field.dataset.stepDisabled;
          }
        });
    };

    const getStepError = (step) => step?.querySelector(".wizard-error");

    const showStepError = (step, message) => {
      if (!step) return;
      let error = getStepError(step);
      if (!error) {
        error = document.createElement("div");
        error.className = "wizard-error";
        step.prepend(error);
      }
      error.textContent = message;
    };

    const clearStepError = (step) => {
      const error = getStepError(step);
      if (error) {
        error.remove();
      }
    };

    const isFieldRequired = (field) =>
      field.required || field.dataset.required === "true";

    const validateStep = (step) => {
      if (!step) return true;
      clearStepError(step);
      const fields = Array.from(step.querySelectorAll("input, select, textarea")).filter(
        (field) => !field.disabled
      );
      let invalidField = null;
      const requiredRadioGroups = new Set();
      for (const field of fields) {
        if (!isFieldRequired(field)) continue;
        if (field.type === "radio") {
          if (field.name) {
            requiredRadioGroups.add(field.name);
          }
          continue;
        }
        if (field.type === "checkbox") continue;
        const value = typeof field.value === "string" ? field.value.trim() : field.value;
        if (!value) {
          invalidField = field;
          break;
        }
      }
      if (!invalidField && requiredRadioGroups.size) {
        for (const name of requiredRadioGroups) {
          const group = fields.filter((field) => field.type === "radio" && field.name === name);
          if (!group.some((field) => field.checked)) {
            invalidField = group[0] || null;
            break;
          }
        }
      }
      if (invalidField) {
        showStepError(step, "Add the required info before continuing.");
        invalidField.focus();
        if (typeof invalidField.select === "function") {
          invalidField.select();
        }
        return false;
      }
      return true;
    };

    const setNotSureSteps = (isEnabled) => {
      notSureSteps.forEach((step) => setStepEnabled(step, isEnabled));
    };

    const resetNotSureSuggestion = () => {
      if (notSureSuggestion) {
        notSureSuggestion.classList.add("hidden");
      }
      if (notSureSuggestionKind) {
        notSureSuggestionKind.textContent = "";
      }
      if (notSureSuggestionText) {
        notSureSuggestionText.textContent = "";
      }
      if (notSureStatus) {
        notSureStatus.textContent = "";
      }
      if (notSureUseBtn) {
        delete notSureUseBtn.dataset.kind;
      }
    };

    const syncKind = (options = {}) => {
      const prevKind = currentKind;
      const kind = form.querySelector('input[name="item_kind"]:checked')?.value;
      const owner = form.querySelector('input[name="owner_type"]:checked')?.value;
      currentKind = kind || "task";
      const isTask = currentKind === "task";
      const isProject = currentKind === "project";
      const isNotSure = currentKind === "not_sure";
      setSectionActive(attachProject, isTask);
      setSectionActive(projectCategory, isProject);
      setSectionActive(projectColor, isProject);
      includeWeekFields.forEach((field) => setSectionActive(field, isProject));
      if (horizonLabel) {
        horizonLabel.textContent = isProject ? "Time horizon" : "When does it belong?";
      }
      horizonNoteTask?.classList.toggle("hidden", isProject);
      horizonNoteProject?.classList.toggle("hidden", !isProject);
      setStepEnabled(blockStep, isTask);
      setNotSureSteps(isNotSure);
      if (isNotSure && prevKind !== "not_sure") {
        notSureDecisionInputs.forEach((input) => {
          input.checked = false;
        });
        resetNotSureSuggestion();
      }
      if (!isNotSure) {
        resetNotSureSuggestion();
      }
      if (waitingField) {
        waitingField.classList.toggle("hidden", owner !== "opp");
        waitingField
          .querySelectorAll("input, select, textarea")
          .forEach((field) => (field.disabled = owner !== "opp"));
      }
      syncHorizon();
      if (options?.targetStep) {
        const activeSteps = getActiveSteps();
        const index = activeSteps.indexOf(options.targetStep);
        if (index >= 0) {
          current = index;
        }
      }
      showStep(current);
    };

    const syncHorizon = () => {
      if (!horizonSelect) return;
      const val = horizonSelect.value;
      const isWeek = val === "week" || val === "today";
      const isProject = currentKind === "project";
      if (!isProject) {
        helperNote?.classList.add("hidden");
        return;
      }
      helperNote?.classList.toggle("hidden", isWeek);
      if (includeRadios.length) {
        includeRadios.forEach((r) => {
          if (isWeek && r.value === "yes") r.checked = true;
          if (!isWeek && r.value === "no") r.checked = true;
        });
      }
    };

    nextBtn?.addEventListener("click", () => {
      const activeSteps = getActiveSteps();
      if (!validateStep(activeSteps[current])) {
        return;
      }
      if (current < activeSteps.length - 1) {
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

    const resetWizard = () => {
      form.reset();
      const sourceInput = form.querySelector('input[name="source_task_id"]');
      if (sourceInput) {
        sourceInput.disabled = !sourceInput.value;
      }
      resetNotSureSuggestion();
      syncKind();
      showStep(0);
    };

    form.addEventListener("wizard-reset", resetWizard);
    form.addEventListener("input", (event) => {
      const step = event.target.closest(".wizard-step");
      clearStepError(step);
    });
    form.addEventListener("submit", (event) => {
      const firstStep = steps.find((step) => step.dataset.step === "1");
      if (!validateStep(firstStep)) {
        showStep(0);
        event.preventDefault();
      }
    });

    notSureDecisionInputs.forEach((input) => {
      input.addEventListener("change", () => {
        const choice = input.value;
        const target = form.querySelector(`input[name="item_kind"][value="${choice}"]`);
        if (!target) return;
        target.checked = true;
        syncKind({ targetStep: horizonStep });
      });
    });

    notSureSuggestBtn?.addEventListener("click", async () => {
      const step = notSureSuggestBtn.closest(".wizard-step");
      const details = (notSureDetails?.value || "").trim();
      clearStepError(step);
      if (!details) {
        showStepError(step, "Share a little more detail so I can suggest a fit.");
        notSureDetails?.focus();
        return;
      }
      if (!csrfToken) {
        showStepError(step, "Missing CSRF token. Refresh and try again.");
        return;
      }
      notSureSuggestBtn.disabled = true;
      if (notSureStatus) notSureStatus.textContent = "Thinking...";
      try {
        const payload = {
          title: form.querySelector('input[name="capture_text"]')?.value || "",
          details,
          size:
            form.querySelector('input[name="not_sure_size"]:checked')?.value || null,
          next_action:
            form.querySelector('input[name="not_sure_next"]:checked')?.value || null,
        };
        const res = await fetch("/capture/wizard/suggest", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-csrf-token": csrfToken || "",
          },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          showStepError(step, data.detail || "Couldn't get a suggestion. Try again.");
          return;
        }
        const kind = data.kind === "project" ? "project" : "task";
        const kindLabel = kind === "project" ? "Project" : "Task";
        const rationale = data.rationale || "You can still choose either way.";
        const suffix = data.engine && data.engine !== "ollama" ? " (quick heuristic)" : "";
        if (notSureSuggestionKind) {
          notSureSuggestionKind.textContent = `${kindLabel}${suffix}`;
        }
        if (notSureSuggestionText) {
          notSureSuggestionText.textContent = rationale;
        }
        if (notSureSuggestion) {
          notSureSuggestion.classList.remove("hidden");
        }
        const decisionInput = notSureDecisionInputs.find((input) => input.value === kind);
        if (decisionInput) {
          decisionInput.checked = true;
        }
        if (notSureUseBtn) {
          notSureUseBtn.dataset.kind = kind;
        }
      } catch (err) {
        showStepError(step, "Couldn't get a suggestion. Try again.");
      } finally {
        notSureSuggestBtn.disabled = false;
        if (notSureStatus) notSureStatus.textContent = "";
      }
    });

    notSureUseBtn?.addEventListener("click", () => {
      const kind = notSureUseBtn.dataset.kind;
      if (!kind) return;
      const decisionInput = notSureDecisionInputs.find((input) => input.value === kind);
      if (!decisionInput) return;
      decisionInput.checked = true;
      decisionInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
    resetWizard();
  }

  const guidedCaptureModal = document.getElementById("guided-capture-modal");
  if (guidedCaptureModal) {
    const openButtons = document.querySelectorAll("[data-guided-capture-open]");
    const closeButtons = guidedCaptureModal.querySelectorAll("[data-guided-capture-close]");
    const form = guidedCaptureModal.querySelector("#wizardForm");
    const input = guidedCaptureModal.querySelector('input[name="capture_text"]');
    const sourceInput = guidedCaptureModal.querySelector('input[name="source_task_id"]');

    const openModal = ({ prefill = "", sourceTaskId = "" } = {}) => {
      form?.dispatchEvent(new Event("wizard-reset"));
      if (input) {
        input.value = prefill || "";
      }
      if (sourceInput) {
        sourceInput.value = sourceTaskId || "";
        sourceInput.disabled = !sourceTaskId;
      }
      guidedCaptureModal.classList.remove("hidden");
      input?.focus();
      input?.select();
    };

    const closeModal = () => {
      guidedCaptureModal.classList.add("hidden");
      form?.dispatchEvent(new Event("wizard-reset"));
    };

    openGuidedCaptureModal = openModal;

    openButtons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const prefill = (button.dataset.guidedPrefill || "").trim();
        const sourceTaskId = button.dataset.guidedSource || "";
        openModal({ prefill, sourceTaskId });
      });
    });

    closeButtons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        closeModal();
      });
    });

    guidedCaptureModal.addEventListener("click", (event) => {
      if (event.target === guidedCaptureModal) {
        closeModal();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !guidedCaptureModal.classList.contains("hidden")) {
        closeModal();
      }
    });

    if (!guidedCaptureModal.classList.contains("hidden")) {
      input?.focus();
      input?.select();
    }
  }

  const quickCaptureModal = document.getElementById("quick-capture-modal");
  if (quickCaptureModal) {
    const openButtons = document.querySelectorAll("[data-quick-capture-open]");
    const closeButtons = quickCaptureModal.querySelectorAll("[data-quick-capture-close]");
    const form = quickCaptureModal.querySelector("[data-quick-capture-form]");
    const input = quickCaptureModal.querySelector("[data-quick-capture-input]");

    const openModal = () => {
      quickCaptureModal.classList.remove("hidden");
      input?.focus();
      input?.select();
    };

    const closeModal = () => {
      quickCaptureModal.classList.add("hidden");
      form?.reset();
    };

    openButtons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        openModal();
      });
    });

    closeButtons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        closeModal();
      });
    });

    quickCaptureModal.addEventListener("click", (event) => {
      if (event.target === quickCaptureModal) {
        closeModal();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !quickCaptureModal.classList.contains("hidden")) {
        closeModal();
      }
    });
  }

  const inboxDetailModal = document.getElementById("inbox-detail-modal");
  if (inboxDetailModal) {
    const modalCard = inboxDetailModal.querySelector(".inbox-detail-card");
    const closeButtons = inboxDetailModal.querySelectorAll("[data-inbox-detail-close]");
    const form = inboxDetailModal.querySelector("[data-inbox-detail-form]");
    const archiveForm = inboxDetailModal.querySelector("[data-inbox-detail-archive-form]");
    const titleEl = inboxDetailModal.querySelector("[data-inbox-detail-name]");
    const descField = form?.querySelector('textarea[name="description"]');
    const previewEl = inboxDetailModal.querySelector("[data-inbox-detail-preview]");
    const idField = form?.querySelector('input[name="task_id"]');
    const archiveIdField = archiveForm?.querySelector('input[name="task_id"]');
    const processLink = inboxDetailModal.querySelector("[data-inbox-detail-process]");

    const escapeHtml = (value) =>
      value.replace(/[&<>"']/g, (ch) => {
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

    const linkifyText = (value = "") => {
      const urlRegex = /(?:https?:\/\/|www\.)[^\s<]+/gi;
      let result = "";
      let lastIndex = 0;
      let match;

      while ((match = urlRegex.exec(value)) !== null) {
        const start = match.index;
        let url = match[0];
        let trailing = "";
        const trailingMatch = url.match(/[.,;:!?)\]]+$/);
        if (trailingMatch && trailingMatch[0]) {
          trailing = trailingMatch[0];
          url = url.slice(0, -trailing.length);
        }
        result += escapeHtml(value.slice(lastIndex, start));
        const href = url.startsWith("http") ? url : `https://${url}`;
        const safeHref = encodeURI(href).replace(/"/g, "%22").replace(/'/g, "%27");
        result += `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a>`;
        result += escapeHtml(trailing);
        lastIndex = start + match[0].length;
      }

      result += escapeHtml(value.slice(lastIndex));
      return result.replace(/\r?\n/g, "<br>");
    };

    const renderPreview = (value = "") => {
      if (!previewEl) return;
      if (!value.trim()) {
        previewEl.innerHTML = '<span class="muted">No description.</span>';
        return;
      }
      previewEl.innerHTML = linkifyText(value);
    };

    const setEditing = (isEditing) => {
      modalCard?.classList.toggle("is-editing", isEditing);
    };

    const openInboxDetail = (item) => {
      if (!item) return;
      const title = item.dataset.inboxTitle || "Inbox item";
      const descEl = item.querySelector("[data-inbox-desc]");
      const desc = descEl ? descEl.textContent : "";
      const taskId = item.dataset.taskId || "";
      if (titleEl) titleEl.textContent = title;
      if (descField) descField.value = desc;
      renderPreview(desc);
      setEditing(false);
      if (idField) idField.value = taskId;
      if (archiveIdField) archiveIdField.value = taskId;
      if (processLink) {
        processLink.dataset.guidedPrefill = title;
        processLink.dataset.guidedSource = taskId;
        processLink.setAttribute("href", `/capture/process/${taskId}`);
      }
      inboxDetailModal.classList.remove("hidden");
      descField?.focus();
    };

    const closeInboxDetail = () => {
      inboxDetailModal.classList.add("hidden");
      form?.reset();
      archiveForm?.reset();
      if (previewEl) previewEl.innerHTML = "";
      setEditing(false);
    };

    processLink?.addEventListener("click", (event) => {
      const taskId = processLink.dataset.guidedSource;
      const prefill = processLink.dataset.guidedPrefill || "";
      if (typeof openGuidedCaptureModal === "function" && taskId) {
        event.preventDefault();
        closeInboxDetail();
        openGuidedCaptureModal({ prefill, sourceTaskId: taskId });
      }
    });

    document.addEventListener("click", (event) => {
      const item = event.target.closest("[data-inbox-item]");
      if (!item) return;
      if (event.target.closest("[data-inbox-action]")) return;
      event.preventDefault();
      openInboxDetail(item);
    });

    closeButtons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        closeInboxDetail();
      });
    });

    previewEl?.addEventListener("click", () => {
      setEditing(true);
      descField?.focus();
    });

    descField?.addEventListener("input", () => {
      renderPreview(descField.value);
    });

    descField?.addEventListener("blur", () => {
      renderPreview(descField.value);
      setEditing(false);
    });

    inboxDetailModal.addEventListener("click", (event) => {
      if (event.target === inboxDetailModal) {
        closeInboxDetail();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !inboxDetailModal.classList.contains("hidden")) {
        closeInboxDetail();
      }
    });
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
    const shouldSkipAutoRefresh = () => {
      if (document.hidden) return true;
      if (document.querySelector(".coach-widget.is-open")) return true;
      if (document.querySelector(".app-modal:not(.hidden)")) return true;
      if (document.querySelector("#quick-capture-modal:not(.hidden)")) return true;
      if (document.querySelector(".task-edit-form:not(.hidden), .project-edit-form:not(.hidden)")) {
        return true;
      }
      if (document.querySelector(".event-edit-form:not(.hidden)")) return true;
      const active = document.activeElement;
      if (active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) {
        return true;
      }
      return false;
    };
    setInterval(() => {
      if (shouldSkipAutoRefresh()) return;
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
    const container = toggle.closest(".task-card, .list-item");
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

  const draggableLists = document.querySelectorAll("[data-draggable-list]");
  if (draggableLists.length) {
    const getAfterElement = (container, y) => {
      const items = [...container.querySelectorAll(".list-item:not(.dragging)")];
      return items.reduce(
        (closest, child) => {
          const box = child.getBoundingClientRect();
          const offset = y - box.top - box.height / 2;
          if (offset < 0 && offset > closest.offset) {
            return { offset, element: child };
          }
          return closest;
        },
        { offset: Number.NEGATIVE_INFINITY, element: null }
      ).element;
    };

    draggableLists.forEach((list) => {
      list.querySelectorAll(".list-item").forEach((item) => {
        item.setAttribute("draggable", "true");
      });

      list.addEventListener("dragstart", (event) => {
        const item = event.target.closest(".list-item");
        if (!item) return;
        item.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
      });

      list.addEventListener("dragend", (event) => {
        const item = event.target.closest(".list-item");
        item?.classList.remove("dragging");
      });

      list.addEventListener("dragover", (event) => {
        event.preventDefault();
        const dragging = list.querySelector(".dragging");
        if (!dragging) return;
        const after = getAfterElement(list, event.clientY);
        if (!after) {
          list.appendChild(dragging);
        } else {
          list.insertBefore(dragging, after);
        }
      });
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
    const historyKey = "sfo:coach-history";
    const nudgeRoot = coachRoot.querySelector("[data-coach-nudges]");
    const modalEl = document.getElementById("app-modal");

    let context = {};
    let historyLoaded = false;
    let historyCache = [];
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

    const sendMessage = async (text) => {
      const message = (text || "").trim();
      if (!message) return;
      addMessage("user", message);
      if (inputEl) inputEl.value = "";
      setStatus("Thinking...");
      const pending = addMessage("assistant", "Thinking...", { persist: false });
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
          setTimeout(() => window.location.reload(), 500);
        }
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
