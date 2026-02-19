document.addEventListener("DOMContentLoaded", () => {
  const isTauriEnv = Boolean(window.__TAURI__ || window.__TAURI_INTERNALS__);
  const dragDebugEnabled = (() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("dragdebug")) {
      const value = params.get("dragdebug");
      if (value === "1") {
        localStorage.setItem("sfo:dragdebug", "1");
      } else if (value === "0") {
        localStorage.setItem("sfo:dragdebug", "0");
      } else {
        localStorage.removeItem("sfo:dragdebug");
      }
    }
    const stored = localStorage.getItem("sfo:dragdebug");
    if (stored === "0") return false;
    if (stored === "1") return true;
    return isTauriEnv;
  })();

  const dragDebugEl = (() => {
    if (!dragDebugEnabled) return null;
    const el = document.createElement("div");
    el.id = "drag-debug";
    el.className = "drag-debug";
    el.textContent = "Drag debug enabled (pointer v2)";
    document.body.appendChild(el);
    return el;
  })();

  const logDrag = (message) => {
    if (!dragDebugEl) return;
    const timestamp = new Date().toLocaleTimeString();
    dragDebugEl.textContent = `${timestamp} ${message}`;
  };

  const pageContent = document.querySelector(".page-content");
  const scrollKey = `sfo:scroll:${window.location.pathname}`;
  const scrollPendingKey = `${scrollKey}:pending`;
  const getScrollTop = () =>
    pageContent ? pageContent.scrollTop : window.scrollY || 0;
  const getMaxScroll = () => {
    if (pageContent) {
      return Math.max(0, pageContent.scrollHeight - pageContent.clientHeight);
    }
    const root = document.documentElement;
    return Math.max(0, (root?.scrollHeight || 0) - window.innerHeight);
  };
  const setScrollTop = (value) => {
    if (pageContent) {
      pageContent.scrollTop = value;
      return;
    }
    window.scrollTo(0, value);
  };
  const persistScroll = () => {
    sessionStorage.setItem(scrollKey, String(getScrollTop()));
    sessionStorage.setItem(scrollPendingKey, "1");
  };

  const savedScroll = sessionStorage.getItem(scrollKey);
  if (savedScroll !== null) {
    const parsed = Number.parseInt(savedScroll, 10);
    if (!Number.isNaN(parsed)) {
      const attemptRestore = (tries = 0) => {
        const maxScroll = getMaxScroll();
        const target = Math.max(0, Math.min(parsed, maxScroll));
        setScrollTop(target);
        const current = getScrollTop();
        const closeEnough = Math.abs(current - target) <= 2;
        if (closeEnough || tries >= 8) {
          sessionStorage.removeItem(scrollKey);
          sessionStorage.removeItem(scrollPendingKey);
          return;
        }
        requestAnimationFrame(() => attemptRestore(tries + 1));
      };
      const scheduleRestore = () => attemptRestore();
      requestAnimationFrame(scheduleRestore);
      window.addEventListener("load", scheduleRestore, { once: true });
      setTimeout(scheduleRestore, 120);
    } else {
      sessionStorage.removeItem(scrollKey);
      sessionStorage.removeItem(scrollPendingKey);
    }
  }

  document.addEventListener(
    "submit",
    (event) => {
      const formEl = event.target instanceof HTMLFormElement ? event.target : null;
      if (!formEl) return;
      if (!formEl.matches("[data-preserve-scroll]")) return;
      if (formEl.matches("[data-async]")) return;
      persistScroll();
    },
    true
  );

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    const submitEl = target.closest(
      "[data-preserve-scroll] button[type=\"submit\"], [data-preserve-scroll] input[type=\"submit\"]"
    );
    if (!submitEl) return;
    const formEl = submitEl.closest("form");
    if (formEl?.matches("[data-async]")) return;
    persistScroll();
  });

  window.addEventListener("pagehide", () => {
    if (sessionStorage.getItem(scrollPendingKey) === "1") {
      sessionStorage.setItem(scrollKey, String(getScrollTop()));
    }
  });

  const ensureToastStack = () => {
    let stack = document.getElementById("toast-stack");
    if (stack) return stack;
    stack = document.createElement("div");
    stack.id = "toast-stack";
    stack.className = "toast-stack";
    document.body.appendChild(stack);
    return stack;
  };

  const showToast = (message, options = {}) => {
    const text = `${message || ""}`.trim();
    if (!text) return;
    const {
      variant = "success",
      timeout = 4200,
      actionLabel = "",
      onAction = null,
    } = options;
    const stack = ensureToastStack();
    const toast = document.createElement("div");
    toast.className = `toast ${variant}`.trim();
    toast.setAttribute("role", "status");
    const messageEl = document.createElement("span");
    messageEl.className = "toast-text";
    messageEl.textContent = text;
    toast.appendChild(messageEl);
    if (actionLabel && typeof onAction === "function") {
      const actionBtn = document.createElement("button");
      actionBtn.type = "button";
      actionBtn.className = "toast-action";
      actionBtn.textContent = actionLabel;
      actionBtn.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        actionBtn.disabled = true;
        try {
          await onAction();
        } finally {
          dismiss();
        }
      });
      toast.appendChild(actionBtn);
    }
    stack.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("is-visible"));

    const dismiss = () => {
      toast.classList.remove("is-visible");
      toast.classList.add("is-exiting");
      setTimeout(() => toast.remove(), 220);
    };

    let timer = null;
    if (timeout > 0) {
      timer = window.setTimeout(dismiss, timeout);
    }
    toast.addEventListener("click", () => {
      if (timer) window.clearTimeout(timer);
      dismiss();
    });
  };

  const moveExistingToasts = () => {
    const existing = Array.from(document.querySelectorAll(".toast"));
    if (!existing.length) return false;
    const stack = ensureToastStack();
    existing.forEach((toast) => {
      if (toast.closest("#toast-stack")) return;
      stack.appendChild(toast);
      requestAnimationFrame(() => toast.classList.add("is-visible"));
      const timer = window.setTimeout(() => {
        toast.classList.remove("is-visible");
        toast.classList.add("is-exiting");
        setTimeout(() => toast.remove(), 220);
      }, 4200);
      toast.addEventListener("click", () => {
        window.clearTimeout(timer);
        toast.classList.remove("is-visible");
        toast.classList.add("is-exiting");
        setTimeout(() => toast.remove(), 220);
      });
    });
    return true;
  };

  const clearFlashQueryParams = () => {
    const url = new URL(window.location.href);
    const params = url.searchParams;
    const hadFlash = params.has("success") || params.has("error");
    if (!hadFlash) return;
    params.delete("success");
    params.delete("error");
    url.search = params.toString();
    window.history.replaceState({}, "", url);
  };

  const showFlashToasts = () => {
    const moved = moveExistingToasts();
    const params = new URLSearchParams(window.location.search);
    if (!moved) {
      const success = params.get("success");
      if (success) showToast(success, { variant: "success" });
    }
    const error = params.get("error");
    if (error) showToast(error, { variant: "error" });
    if (params.has("success") || params.has("error")) {
      clearFlashQueryParams();
    }
  };

  showFlashToasts();
  window.showToast = showToast;

  const updateInboxCount = (count) => {
    if (typeof count !== "number") return;
    const pill = document.querySelector(".inbox-count");
    if (!pill) return;
    pill.textContent = String(count);
  };

  const updateInboxEmptyState = () => {
    const list = document.querySelector(".inbox-panel .list");
    if (!list) return;
    const hasItems = list.querySelector("[data-inbox-item]") !== null;
    const emptyEl = list.querySelector(":scope > .inbox-empty, :scope > .muted");
    if (hasItems) {
      emptyEl?.remove();
      return;
    }
    if (!emptyEl) {
      const empty = document.createElement("div");
      empty.className = "muted inbox-empty";
      empty.textContent = "Inbox clear.";
      list.appendChild(empty);
    }
  };

  const updateInboxDescription = (taskId, description) => {
    if (!taskId) return;
    const item = document.querySelector(
      `[data-inbox-item][data-task-id="${taskId}"]`
    );
    if (!item) return;
    const descEl = item.querySelector("[data-inbox-desc]");
    if (descEl) {
      descEl.textContent = description || "";
    }
  };

  const removeInboxItem = (taskId) => {
    if (!taskId) return;
    const item = document.querySelector(
      `[data-inbox-item][data-task-id="${taskId}"]`
    );
    if (item) item.remove();
    updateInboxEmptyState();
  };

  const csrfToken =
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

  const postInboxUndo = async (taskId) => {
    const formData = new FormData();
    formData.append("task_id", String(taskId));
    if (csrfToken) {
      formData.append("csrf_token", csrfToken);
    }
    const response = await fetch("/inbox/undo", {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "fetch",
        Accept: "application/json",
      },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false || payload.status === "error") {
      throw new Error(payload.message || payload.error || "Could not undo.");
    }
    return payload;
  };

  const handleAsyncFormSubmit = async (form, event) => {
    if (form.dataset.asyncPending === "1") return;
    event.preventDefault();
    form.dataset.asyncPending = "1";
    const submitButtons = form.querySelectorAll(
      "button[type=\"submit\"], input[type=\"submit\"]"
    );
    submitButtons.forEach((btn) => {
      btn.disabled = true;
    });

    try {
      const action = form.getAttribute("action") || window.location.pathname;
      const method = (form.getAttribute("method") || "post").toUpperCase();
      const formData = new FormData(form);
      const response = await fetch(action, {
        method,
        body: formData,
        headers: {
          "X-Requested-With": "fetch",
          Accept: "application/json",
        },
      });
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        form.submit();
        return;
      }
      const payload = await response.json();
      if (!response.ok || payload.ok === false || payload.status === "error") {
        showToast(payload.message || payload.error || "Something went wrong.", {
          variant: "error",
        });
        return;
      }

      if (typeof payload.inbox_count === "number") {
        updateInboxCount(payload.inbox_count);
      }

      if (payload.description !== undefined && payload.task_id) {
        updateInboxDescription(payload.task_id, payload.description);
        document.dispatchEvent(
          new CustomEvent("inbox:updated", { detail: { taskId: payload.task_id } })
        );
      }

      if (payload.removed && payload.task_id) {
        let removedItem = null;
        let removedParent = null;
        const removeClosest = form.dataset.removeClosest;
        if (removeClosest) {
          removedItem = form.closest(removeClosest);
          removedParent = removedItem?.parentElement || null;
          removedItem?.remove();
          updateInboxEmptyState();
        } else {
          removedItem = document.querySelector(
            `[data-inbox-item][data-task-id="${payload.task_id}"]`
          );
          removedParent = removedItem?.parentElement || null;
          removeInboxItem(payload.task_id);
        }
        document.dispatchEvent(
          new CustomEvent("inbox:archived", { detail: { taskId: payload.task_id } })
        );
        const removedMarkup = removedItem?.outerHTML || "";
        if (payload.message) {
          if (payload.undo_available && removedMarkup && removedParent) {
            showToast(payload.message, {
              variant: "success",
              timeout: 9000,
              actionLabel: "Undo",
              onAction: async () => {
                try {
                  const undoPayload = await postInboxUndo(payload.task_id);
                  if (typeof undoPayload.inbox_count === "number") {
                    updateInboxCount(undoPayload.inbox_count);
                  }
                  const temp = document.createElement("div");
                  temp.innerHTML = removedMarkup;
                  const restored = temp.firstElementChild;
                  if (undoPayload.restored && restored) {
                    removedParent.prepend(restored);
                    updateInboxEmptyState();
                    document.dispatchEvent(
                      new CustomEvent("inbox:restored", {
                        detail: { taskId: payload.task_id },
                      })
                    );
                  }
                  if (undoPayload.message) {
                    showToast(undoPayload.message, { variant: "success", timeout: 2400 });
                  }
                } catch (error) {
                  showToast(error.message || "Could not undo.", { variant: "error" });
                }
              },
            });
          } else {
            showToast(payload.message, { variant: "success" });
          }
        }
        return;
      }

      if (payload.message) {
        showToast(payload.message, { variant: "success" });
      }
    } catch (error) {
      showToast("Something went wrong. Please try again.", { variant: "error" });
    } finally {
      form.dataset.asyncPending = "";
      submitButtons.forEach((btn) => {
        btn.disabled = false;
      });
    }
  };

  document.addEventListener("submit", (event) => {
    const form = event.target instanceof HTMLFormElement ? event.target : null;
    if (!form) return;
    if (!form.matches("[data-async]")) return;
    handleAsyncFormSubmit(form, event);
  });

  const setGlobalDragging = (isDragging) => {
    document.body.classList.toggle("dragging", Boolean(isDragging));
  };

  if (dragDebugEl) {
    document.addEventListener("pointerdown", (event) => {
      const target = event.target.closest("[data-task-card], .list-item");
      if (!target) return;
      logDrag("pointerdown");
    });
  }

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
    const horizonOptionConfigs = horizonSelect
      ? Array.from(horizonSelect.options).map((option) => ({
          option,
          horizonFor: option.dataset.horizonFor || "both",
        }))
      : [];
    const includeRadios = form.querySelectorAll('input[name="include_this_week"]');
    const includeWeekFields = form.querySelectorAll("[data-include-week]");
    const helperNote = form.querySelector(".note.helper");
    const horizonLabel = form.querySelector("[data-horizon-label]");
    const horizonNoteTask = form.querySelector("[data-horizon-note-task]");
    const horizonNoteProject = form.querySelector("[data-horizon-note-project]");
    const blockStep = form.querySelector('.wizard-step[data-step="5"]');
    const whyStep = form.querySelector('.wizard-step[data-step="4"]');
    const projectLinkNote = form.querySelector("[data-project-link-note]");
    const projectSelectField = form.querySelector('select[name="project_id"]');
    const blockTypeSelect = form.querySelector('select[name="block_type"]');
    const blockGuidance = form.querySelector("[data-block-guidance]");
    const captureTitleInput = form.querySelector('input[name="capture_text"]');
    const captureDescriptionInput = form.querySelector('textarea[name="capture_description"]');
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
    const sourceTaskInput = form.querySelector('input[name="source_task_id"]');
    const sourceIntentSection = form.querySelector("[data-source-intent]");
    const sourceIntentInputs = Array.from(
      form.querySelectorAll("[data-source-intent-input]")
    );
    const defaultIntentInput = form.querySelector("[data-inbox-intent-default]");
    const supportOnlySections = Array.from(
      form.querySelectorAll("[data-support-project-only]")
    );
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");

    let current = 0;
    let currentKind = "task";
    let blockTypeManuallySet = false;

    const waitingField = form.querySelector("[data-waiting-person]");

    const getActiveSteps = () =>
      steps.filter((step) => step.dataset.stepDisabled !== "true");

    const isSourceTaskMode = () => {
      const value = sourceTaskInput?.value || "";
      return value.trim().length > 0;
    };

    const selectedInboxIntent = () =>
      sourceIntentInputs.find((input) => input.checked)?.value || "";

    const syncSourceIntentMode = () => {
      const sourceMode = isSourceTaskMode();
      sourceIntentSection?.classList.toggle("hidden", !sourceMode);
      if (defaultIntentInput) {
        defaultIntentInput.disabled = sourceMode;
      }
      sourceIntentInputs.forEach((input) => {
        input.disabled = !sourceMode;
        if (!sourceMode) {
          input.checked = false;
        }
      });
    };

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

    const inferBlockTypeSuggestion = () => {
      const sourceText = `${captureTitleInput?.value || ""} ${captureDescriptionInput?.value || ""}`
        .toLowerCase()
        .trim();
      if (!sourceText) {
        return { type: "focus", reason: "default for meaningful work." };
      }
      if (/(call|meeting|chat|talk|interview|1:1|one-on-one)/.test(sourceText)) {
        return { type: "social", reason: "it sounds conversation-based." };
      }
      if (/(email|invoice|admin|follow[ -]?up|schedule|book|organi[sz]e|paperwork|forms?)/.test(sourceText)) {
        return { type: "admin", reason: "it sounds operational/logistics-heavy." };
      }
      if (/(recover|rest|sleep|walk|stretch|wellbeing|recharge|reset)/.test(sourceText)) {
        return { type: "recovery", reason: "it sounds energy/rest oriented." };
      }
      return { type: "focus", reason: "it likely needs focused attention." };
    };

    const syncBlockGuidance = () => {
      if (!blockGuidance) return;
      const suggestion = inferBlockTypeSuggestion();
      const title = suggestion.type.charAt(0).toUpperCase() + suggestion.type.slice(1);
      blockGuidance.textContent = `Suggested: ${title} - ${suggestion.reason}`;
      if (blockTypeSelect && !blockTypeManuallySet) {
        blockTypeSelect.value = suggestion.type;
      }
    };

    const syncHorizonOptions = () => {
      if (!horizonSelect || !horizonOptionConfigs.length) return;
      const mode = currentKind === "project" ? "project" : "task";
      let hasCurrent = false;
      let firstVisibleValue = "";
      horizonOptionConfigs.forEach(({ option, horizonFor }) => {
        const visible = horizonFor === "both" || horizonFor === mode;
        option.hidden = !visible;
        option.disabled = !visible;
        if (visible && !firstVisibleValue) {
          firstVisibleValue = option.value;
        }
        if (visible && option.value === horizonSelect.value) {
          hasCurrent = true;
        }
      });
      if (!hasCurrent && firstVisibleValue) {
        horizonSelect.value = firstVisibleValue;
      }
    };

    const syncKind = (options = {}) => {
      syncSourceIntentMode();
      const prevKind = currentKind;
      const kind = form.querySelector('input[name="item_kind"]:checked')?.value;
      const owner = form.querySelector('input[name="owner_type"]:checked')?.value;
      const sourceMode = isSourceTaskMode();
      const intent = selectedInboxIntent();
      const nextKind = kind || "task";
      const supportsProjectFlow = !sourceMode || !intent || intent === "support_project";
      const supportsProjectTask =
        sourceMode && intent === "support_project" && nextKind === "task";
      currentKind = nextKind;
      const isTask = supportsProjectFlow && currentKind === "task";
      const isProject = supportsProjectFlow && currentKind === "project";
      const isDecideLater = supportsProjectFlow && currentKind === "decide_later";
      const isNotSure = supportsProjectFlow && currentKind === "not_sure";
      supportOnlySections.forEach((section) => setSectionActive(section, supportsProjectFlow));
      setSectionActive(attachProject, isTask);
      setSectionActive(projectCategory, isProject);
      setSectionActive(projectColor, isProject);
      if (projectSelectField) {
        projectSelectField.required = Boolean(supportsProjectTask);
      }
      projectLinkNote?.classList.toggle("hidden", !supportsProjectTask);
      includeWeekFields.forEach((field) => setSectionActive(field, isProject));
      if (horizonLabel) {
        horizonLabel.textContent = isProject ? "Time horizon" : "When does it belong?";
      }
      horizonNoteTask?.classList.toggle("hidden", isProject);
      horizonNoteProject?.classList.toggle("hidden", !isProject);
      syncHorizonOptions();
      setStepEnabled(horizonStep, supportsProjectFlow && !isDecideLater);
      setStepEnabled(whyStep, false);
      setStepEnabled(blockStep, isTask);
      setNotSureSteps(supportsProjectFlow && isNotSure);
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
      syncBlockGuidance();
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
    sourceIntentInputs.forEach((input) => input.addEventListener("change", syncKind));
    form.querySelectorAll('input[name="owner_type"]').forEach((r) =>
      r.addEventListener("change", syncKind)
    );
    horizonSelect?.addEventListener("change", syncHorizon);
    captureTitleInput?.addEventListener("input", syncBlockGuidance);
    captureDescriptionInput?.addEventListener("input", syncBlockGuidance);
    blockTypeSelect?.addEventListener("change", () => {
      blockTypeManuallySet = true;
    });

    const resetWizard = () => {
      form.reset();
      if (sourceTaskInput) {
        sourceTaskInput.disabled = !sourceTaskInput.value;
      }
      blockTypeManuallySet = false;
      resetNotSureSuggestion();
      syncKind();
      showStep(0);
    };

    form.addEventListener("wizard-reset", resetWizard);
    form.addEventListener("wizard-sync", syncKind);
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
    const nextUrlInput = guidedCaptureModal.querySelector('input[name="next_url"]');
    const projectSelect = guidedCaptureModal.querySelector('select[name="project_id"]');

    const openModal = ({ prefill = "", sourceTaskId = "", nextUrl = "", projectId = "" } = {}) => {
      form?.dispatchEvent(new Event("wizard-reset"));
      if (input) {
        input.value = prefill || "";
      }
      if (sourceInput) {
        sourceInput.value = sourceTaskId || "";
        sourceInput.disabled = !sourceTaskId;
      }
      if (nextUrlInput) {
        nextUrlInput.value = nextUrl || "";
      }
      if (projectSelect) {
        projectSelect.value = projectId || "";
      }
      form?.dispatchEvent(new Event("wizard-sync"));
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
        const nextUrl = button.dataset.guidedNextUrl || window.location.pathname;
        const projectId = button.dataset.guidedProjectId || "";
        openModal({ prefill, sourceTaskId, nextUrl, projectId });
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

  const recycleEmptyModal = document.getElementById("recycle-empty-modal");
  if (recycleEmptyModal) {
    const openButtons = document.querySelectorAll("[data-recycle-empty-open]");
    const closeButtons = recycleEmptyModal.querySelectorAll("[data-recycle-empty-close]");

    const openModal = () => {
      recycleEmptyModal.classList.remove("hidden");
      closeButtons[0]?.focus();
    };

    const closeModal = () => {
      recycleEmptyModal.classList.add("hidden");
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

    recycleEmptyModal.addEventListener("click", (event) => {
      if (event.target === recycleEmptyModal) {
        closeModal();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !recycleEmptyModal.classList.contains("hidden")) {
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
    const routeForms = inboxDetailModal.querySelectorAll("[data-inbox-detail-route-form]");
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
      routeForms.forEach((routeForm) => {
        const routeTaskField = routeForm.querySelector('input[name="task_id"]');
        if (routeTaskField) {
          routeTaskField.value = taskId;
        }
      });
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

    const matchesOpenTask = (taskId) =>
      Boolean(taskId && idField && idField.value === String(taskId));

    document.addEventListener("inbox:updated", (event) => {
      if (!matchesOpenTask(event.detail?.taskId)) return;
      closeInboxDetail();
    });

    document.addEventListener("inbox:archived", (event) => {
      if (!matchesOpenTask(event.detail?.taskId)) return;
      closeInboxDetail();
    });

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
      if (inboxDragInProgress) return;
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

  const setInboxSelection = (item) => {
    document
      .querySelectorAll("[data-inbox-item].is-selected")
      .forEach((node) => node.classList.remove("is-selected"));
    if (!item) return;
    item.classList.add("is-selected");
  };

  document.addEventListener("click", (event) => {
    const item = event.target.closest("[data-inbox-item]");
    if (!item) return;
    setInboxSelection(item);
  });

  const inboxShortcutItem = () => {
    const selected = document.querySelector("[data-inbox-item].is-selected");
    if (selected) return selected;
    return document.querySelector("[data-inbox-item]");
  };

  const isTypingTarget = (target) => {
    if (!(target instanceof Element)) return false;
    if (target.closest(".coach-panel")) return true;
    return Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
  };

  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented) return;
    if (isTypingTarget(event.target)) return;
    if (document.querySelector(".app-modal:not(.hidden)")) return;
    const key = (event.key || "").toLowerCase();
    if (!["p", "l", "e", "k", "d"].includes(key)) return;
    const item = inboxShortcutItem();
    if (!item) return;
    const target = item.querySelector(`[data-inbox-shortcut="${key}"]`);
    if (!target) return;
    event.preventDefault();
    setInboxSelection(item);
    if (target.closest("form")) {
      const form = target.closest("form");
      if (typeof form?.requestSubmit === "function") {
        form.requestSubmit();
        return;
      }
      target.click();
      return;
    }
    target.click();
  });

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

    submitBtn?.addEventListener("click", (event) => {
      if (submitBtn.classList.contains("hidden")) return;
      if (typeof onboardingForm.requestSubmit === "function") {
        event.preventDefault();
        onboardingForm.requestSubmit();
      }
    });

    onboardingForm.addEventListener("submit", () => {
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Saving...";
      }
    });

    showStep(0);
  }

  const tasksToggle = document.querySelector("[data-task-toggle]");
  const tasksBoardView = document.querySelector("[data-task-board]");
  if (tasksToggle && tasksBoardView) {
    tasksToggle.querySelectorAll("[data-view]").forEach((button) => {
      button.addEventListener("click", () => {
        const view = button.dataset.view;
        if (!view || tasksBoardView.dataset.view === view) return;
        tasksBoardView.dataset.view = view;
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
  const dayCalendarScroll = document.querySelector(".day-calendar-scroll");
  let dayCalendarAutoScrolled = false;

  const scrollDayCalendarToNow = () => {
    if (dayCalendarAutoScrolled) return;
    if (!dayCalendarScroll || !nowLine) return;
    if (dayCalendarScroll.scrollHeight <= dayCalendarScroll.clientHeight + 1) return;

    // Keep current time slightly below the top edge so surrounding context is visible.
    const nowOffsetTop = nowLine.offsetTop;
    const topBuffer = Math.round(dayCalendarScroll.clientHeight * 0.35);
    const maxScroll = dayCalendarScroll.scrollHeight - dayCalendarScroll.clientHeight;
    const targetScroll = Math.max(0, Math.min(maxScroll, nowOffsetTop - topBuffer));
    dayCalendarScroll.scrollTop = targetScroll;
    dayCalendarAutoScrolled = true;
  };

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
  requestAnimationFrame(() => {
    requestAnimationFrame(scrollDayCalendarToNow);
  });
  window.addEventListener("load", scrollDayCalendarToNow, { once: true });
  setTimeout(scrollDayCalendarToNow, 120);
  setInterval(updateClock, 1000);

  // Avoid disruptive hard reloads; nudge for manual refresh if the calendar may be stale.
  const hasCalendar = document.querySelector(".calendar-panel, .week-calendar-panel");
  if (hasCalendar) {
    let refreshHintShown = false;
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
      if (refreshHintShown) return;
      showToast("Calendar may have changed. Refresh when convenient.", {
        variant: "success",
        timeout: 4800,
      });
      refreshHintShown = true;
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

  let taskDragInProgress = false;
  let horizonDragInProgress = false;
  let inboxDragInProgress = false;
  const projectEditModal = document.getElementById("project-edit-modal");
  if (projectEditModal) {
    const modalBody = projectEditModal.querySelector("[data-project-edit-body]");
    const closeButtons = projectEditModal.querySelectorAll("[data-project-edit-close]");
    let activeForm = null;
    let activeHost = null;

    const openProjectEditModal = (card) => {
      if (!modalBody || !card) return;
      const form = card.querySelector(".project-edit-form");
      if (!form) return;
      activeForm = form;
      activeHost = form.parentElement;
      form.classList.remove("hidden");
      modalBody.appendChild(form);
      projectEditModal.classList.remove("hidden");
      const input = form.querySelector('input[name="title"]');
      input?.focus();
      input?.select();
    };

    const closeProjectEditModal = () => {
      projectEditModal.classList.add("hidden");
      if (activeForm && activeHost) {
        activeForm.classList.add("hidden");
        activeHost.appendChild(activeForm);
      }
      activeForm = null;
      activeHost = null;
    };

    document.addEventListener("click", (event) => {
      const card = event.target.closest(".horizon-item.project-edit");
      if (!card) return;
      if (horizonDragInProgress) return;
      if (
        event.target.closest(
          ".project-edit-form, .project-edit-actions, input, select, textarea, a"
        )
      ) {
        return;
      }
      event.preventDefault();
      openProjectEditModal(card);
    });

    closeButtons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        closeProjectEditModal();
      });
    });

    projectEditModal.addEventListener("click", (event) => {
      if (event.target === projectEditModal) {
        closeProjectEditModal();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !projectEditModal.classList.contains("hidden")) {
        closeProjectEditModal();
      }
    });
  }
  const taskEditModal = document.querySelector("#task-edit-modal");
  if (taskEditModal) {
    const taskEditForm = taskEditModal.querySelector("[data-task-edit-form]");
    const closeButton = taskEditModal.querySelector("[data-task-edit-close]");
    const titleInput = taskEditForm?.querySelector('input[name="verb_noun"]');
    const descriptionInput = taskEditForm?.querySelector('textarea[name="description"]');
    const taskIdInput = taskEditForm?.querySelector('input[name="task_id"]');
    const projectSelect = taskEditForm?.querySelector('select[name="project_id"]');
    const whenSelect = taskEditForm?.querySelector('select[name="when_bucket"]');
    const blockSelect = taskEditForm?.querySelector('select[name="block_type"]');
    const durationInput = taskEditForm?.querySelector('input[name="duration_minutes"]');
    const alignmentSelect = taskEditForm?.querySelector('select[name="alignment"]');
    const frogCheckbox = taskEditForm?.querySelector('input[name="frog"]');
    const sendToInboxButton = taskEditForm?.querySelector("[data-task-send-inbox]");

    const setSelectValue = (select, value) => {
      if (!select) return;
      select.value = value ?? "";
      if (value && select.value !== value) {
        select.value = "";
      }
    };

    const openTaskEditModal = (card) => {
      if (!taskEditForm || !card) return;
      const data = card.dataset;
      const title = data.taskTitle || "";
      const description = data.taskDescription || "";
      const projectId = data.taskProjectId || "";
      const whenBucket = data.taskWhen || "today";
      const blockType = data.taskBlockType || "";
      const duration = data.taskDuration || "";
      const alignment = data.taskAlignment || "";
      const frog = data.taskFrog === "true";
      const inInbox = data.taskInInbox === "true";

      if (taskIdInput) taskIdInput.value = data.taskId || "";
      if (titleInput) titleInput.value = title;
      if (descriptionInput) descriptionInput.value = description;
      setSelectValue(projectSelect, projectId);
      setSelectValue(whenSelect, whenBucket);
      setSelectValue(blockSelect, blockType);
      if (durationInput) durationInput.value = duration;
      setSelectValue(alignmentSelect, alignment);
      if (frogCheckbox) frogCheckbox.checked = frog;
      if (sendToInboxButton) {
        sendToInboxButton.classList.toggle("hidden", inInbox);
        sendToInboxButton.disabled = inInbox;
      }

      taskEditModal.classList.remove("hidden");
      titleInput?.focus();
      titleInput?.select();
    };

    const closeTaskEditModal = () => {
      if (!taskEditForm) return;
      taskEditModal.classList.add("hidden");
      taskEditForm.reset();
      if (taskIdInput) taskIdInput.value = "";
      sendToInboxButton?.classList.add("hidden");
      sendToInboxButton?.setAttribute("disabled", "true");
    };

    document.addEventListener("click", (event) => {
      if (taskDragInProgress) return;
      if (event.target.closest("[data-task-action]")) return;
      const card = event.target.closest("[data-task-card]");
      if (!card) return;
      event.preventDefault();
      openTaskEditModal(card);
    });

    closeButton?.addEventListener("click", closeTaskEditModal);
    taskEditModal.addEventListener("click", (event) => {
      if (event.target === taskEditModal) {
        closeTaskEditModal();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !taskEditModal.classList.contains("hidden")) {
        closeTaskEditModal();
      }
    });
  }

  const tasksBoard = document.querySelector(".tasks-board");
  if (tasksBoard && tasksBoard.dataset.dragReady !== "main") {
    tasksBoard.dataset.dragReady = "main";
    const usePointerDrag = isTauriEnv;
    tasksBoard.querySelectorAll("[data-task-card]").forEach((card) => {
      if (usePointerDrag) {
        card.removeAttribute("draggable");
      } else {
        card.setAttribute("draggable", "true");
      }
    });
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
    let dragCard = null;
    let dragOrigin = null;
    let dropColumn = null;
    let dropBody = null;
    let dropHandled = false;
    const placeholder = document.createElement("div");
    placeholder.className = "task-drop-placeholder";
    placeholder.setAttribute("aria-hidden", "true");
    const isWithinTasksBoard = (node) => Boolean(node && tasksBoard.contains(node));

    const getAfterElement = (container, y) => {
      const items = [
        ...container.querySelectorAll('[data-task-card]:not(.is-dragging)'),
      ];
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

    const updateColumnCounts = () => {
      tasksBoard.querySelectorAll("[data-tasks-column]").forEach((column) => {
        const pill = column.querySelector(".tasks-column-header .pill");
        if (!pill) return;
        const count = column.querySelectorAll("[data-task-card]").length;
        pill.textContent = String(count);
      });
    };

    const updateEmptyStates = () => {
      tasksBoard.querySelectorAll("[data-tasks-column-body]").forEach((body) => {
        const hasTasks = body.querySelector("[data-task-card]") !== null;
        const empty = body.querySelector(".tasks-empty");
        if (hasTasks && empty) {
          empty.remove();
          return;
        }
        if (!hasTasks && !empty) {
          const message = body.dataset.emptyMessage || "No tasks yet.";
          const placeholder = document.createElement("div");
          placeholder.className = "muted tasks-empty";
          placeholder.textContent = message;
          body.appendChild(placeholder);
        }
      });
    };

    const updateWhenPill = (card, whenValue) => {
      const pill = card?.querySelector(".task-when-pill");
      if (!pill || !whenValue) return;
      pill.textContent = `${whenValue.charAt(0).toUpperCase()}${whenValue.slice(1)}`;
    };

    const clearDropTargets = () => {
      tasksBoard
        .querySelectorAll(".is-drop-target")
        .forEach((el) => el.classList.remove("is-drop-target"));
    };

    const finalizeDrag = () => {
      if (dragCard) {
        dragCard.classList.remove("is-dragging");
      }
      placeholder.remove();
      dragCard = null;
      dragOrigin = null;
      dropColumn = null;
      dropBody = null;
      dropHandled = false;
      clearDropTargets();
      setTimeout(() => {
        taskDragInProgress = false;
      }, 80);
    };

    const revertToOrigin = () => {
      if (!dragOrigin?.body || !dragCard) return;
      if (dragOrigin.nextSibling) {
        dragOrigin.body.insertBefore(dragCard, dragOrigin.nextSibling);
      } else {
        dragOrigin.body.appendChild(dragCard);
      }
    };

    const commitMove = async (column, body) => {
      if (!dragCard || !column || !body) {
        finalizeDrag();
        return;
      }

      if (placeholder.parentNode === body) {
        body.insertBefore(dragCard, placeholder);
      } else {
        body.appendChild(dragCard);
      }
      placeholder.remove();

      const viewMode = tasksBoard.dataset.view || "time";
      const card = dragCard;
      const taskId = card.dataset.taskId;
      const currentWhen = dragOrigin?.when || card.dataset.taskWhen || "today";
      const currentProject = dragOrigin?.project || card.dataset.taskProjectId || "";

      let targetWhen = currentWhen;
      let targetProject = currentProject;

      if (viewMode === "time") {
        targetWhen = column.dataset.whenBucket || currentWhen;
      } else if (viewMode === "project") {
        targetProject = column.dataset.projectId ?? "";
      }

      updateColumnCounts();
      updateEmptyStates();

      if (targetWhen === currentWhen && String(targetProject) === String(currentProject)) {
        finalizeDrag();
        return;
      }

      if (!csrfToken) {
        showToast("Missing CSRF token. Refresh and try again.", { variant: "error" });
        revertToOrigin();
        updateColumnCounts();
        updateEmptyStates();
        finalizeDrag();
        return;
      }

      const formData = new FormData();
      formData.append("csrf_token", csrfToken);
      formData.append("task_id", taskId || "");
      formData.append("when_bucket", targetWhen);
      formData.append("project_id", targetProject);
      formData.append("next_url", window.location.pathname);

      const isTauri = Boolean(window.__TAURI__ || window.__TAURI_INTERNALS__);
      if (isTauri) {
        card.dataset.taskWhen = targetWhen;
        card.dataset.taskProjectId = targetProject;
        if (viewMode === "time") {
          updateWhenPill(card, targetWhen);
        }
        updateColumnCounts();
        updateEmptyStates();
        const form = document.createElement("form");
        form.method = "post";
        form.action = "/tasks/update";
        form.style.display = "none";
        for (const [key, value] of formData.entries()) {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = key;
          input.value = String(value ?? "");
          form.appendChild(input);
        }
        document.body.appendChild(form);
        finalizeDrag();
        form.submit();
        return;
      }

      try {
        const response = await fetch("/tasks/update", {
          method: "POST",
          body: formData,
          credentials: "same-origin",
          headers: {
            "x-csrf-token": csrfToken || "",
            "x-requested-with": "fetch",
            accept: "application/json",
          },
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          showToast(detail.detail || "Unable to move the task. Try again.", {
            variant: "error",
          });
          revertToOrigin();
          updateColumnCounts();
          updateEmptyStates();
          finalizeDrag();
          return;
        }
        card.dataset.taskWhen = targetWhen;
        card.dataset.taskProjectId = targetProject;
        if (viewMode === "time") {
          updateWhenPill(card, targetWhen);
        }
        updateColumnCounts();
        updateEmptyStates();
      } catch (err) {
        showToast("Unable to move the task. Check your connection and try again.", {
          variant: "error",
        });
        revertToOrigin();
        updateColumnCounts();
        updateEmptyStates();
      } finally {
        finalizeDrag();
      }
    };

    const getColumnFromPoint = (x, y) => {
      const columns = tasksBoard.querySelectorAll("[data-tasks-column]");
      for (const column of columns) {
        const rect = column.getBoundingClientRect();
        if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
          return column;
        }
      }
      return null;
    };

    if (usePointerDrag) {
      let pointerId = null;
      let startX = 0;
      let startY = 0;
      let dragging = false;
      let dragCardStyle = "";
      let ghostOffsetX = 0;
      let ghostOffsetY = 0;
      const dragCursorOffsetY = 115;
      const dragThreshold = 6;

      const shouldIgnorePointer = (event) =>
        Boolean(
          event.target.closest(
            "[data-task-action], button, a, input, textarea, select"
          )
        );

      const resetPointer = () => {
        pointerId = null;
        startX = 0;
        startY = 0;
        dragging = false;
        ghostOffsetX = 0;
        ghostOffsetY = 0;
        dragCardStyle = "";
      };

      const updateGhostPosition = (event) => {
        if (!dragCard || !dragging) return;
        dragCard.style.left = `${event.clientX - ghostOffsetX}px`;
        dragCard.style.top = `${event.clientY - ghostOffsetY}px`;
      };

      const beginDrag = (event) => {
        if (!dragCard || !event) return;
        dragging = true;
        taskDragInProgress = true;
        dragCard.classList.add("is-dragging");
        dragCard.classList.add("drag-lift");
        setGlobalDragging(true);
        placeholder.style.height = `${dragCard.offsetHeight}px`;
        if (dragOrigin?.body) {
          dragOrigin.body.insertBefore(placeholder, dragCard);
        }
        dragCardStyle = dragCard.getAttribute("style") || "";
        const rect = dragCard.getBoundingClientRect();
        ghostOffsetX = event.clientX - rect.left;
        ghostOffsetY = event.clientY - rect.top + dragCursorOffsetY;
        document.body.appendChild(dragCard);
        dragCard.style.position = "fixed";
        dragCard.style.width = `${rect.width}px`;
        dragCard.style.height = `${rect.height}px`;
        dragCard.style.left = `${rect.left}px`;
        dragCard.style.top = `${rect.top}px`;
        dragCard.style.pointerEvents = "none";
        updateGhostPosition(event);
        logDrag(`task dragstart ${dragCard.dataset.taskId || ""}`);
      };

      const handlePointerMove = (event) => {
        if (!dragCard || pointerId !== event.pointerId) return;
        const dx = event.clientX - startX;
        const dy = event.clientY - startY;
        if (!dragging) {
          if (Math.hypot(dx, dy) < dragThreshold) return;
          beginDrag(event);
        }
        event.preventDefault();
        updateGhostPosition(event);
        const target = document.elementFromPoint(event.clientX, event.clientY);
        const column =
          target?.closest?.("[data-tasks-column]") ||
          getColumnFromPoint(event.clientX, event.clientY);
        if (!column || !isWithinTasksBoard(column)) {
          clearDropTargets();
          dropColumn = null;
          dropBody = null;
          placeholder.remove();
          return;
        }
        const body =
          target.closest("[data-tasks-column-body]") ||
          column.querySelector("[data-tasks-column-body]");
        if (!body) return;
        clearDropTargets();
        column.classList.add("is-drop-target");
        const after = getAfterElement(body, event.clientY);
        if (!after) {
          body.appendChild(placeholder);
        } else {
          body.insertBefore(placeholder, after);
        }
        const prevColumn = dropColumn;
        dropBody = body;
        dropColumn = column;
        if (prevColumn !== column) {
          logDrag(
            `task dragover ${column.dataset.whenBucket || column.dataset.projectId || ""}`
          );
        }
      };

      const finishPointerDrag = async (event, cancelled = false) => {
        if (!dragCard || pointerId !== event.pointerId) return;
        if (dragCard.releasePointerCapture) {
          try {
            dragCard.releasePointerCapture(pointerId);
          } catch (err) {
            // Ignore pointer capture release errors.
          }
        }
        if (!dragging) {
          dragCard = null;
          dragOrigin = null;
          resetPointer();
          setGlobalDragging(false);
          return;
        }
        dragCard.classList.remove("drag-lift");
        if (dragCardStyle) {
          dragCard.setAttribute("style", dragCardStyle);
        } else {
          dragCard.removeAttribute("style");
        }
        logDrag("task dragend");
        if (cancelled || !dropColumn || !dropBody) {
          revertToOrigin();
          updateColumnCounts();
          updateEmptyStates();
          finalizeDrag();
          resetPointer();
          setGlobalDragging(false);
          return;
        }
        dropHandled = true;
        logDrag("task drop");
        await commitMove(dropColumn, dropBody);
        resetPointer();
        setGlobalDragging(false);
      };

      tasksBoard.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || event.isPrimary === false) return;
        if (shouldIgnorePointer(event)) return;
        const card = event.target.closest("[data-task-card]");
        if (!card || !isWithinTasksBoard(card)) return;
        dragCard = card;
        dragOrigin = {
          body: card.closest("[data-tasks-column-body]"),
          nextSibling: card.nextElementSibling,
          when: card.dataset.taskWhen || "today",
          project: card.dataset.taskProjectId || "",
        };
        pointerId = event.pointerId;
        startX = event.clientX;
        startY = event.clientY;
        dropColumn = null;
        dropBody = null;
        if (dragCard.setPointerCapture) {
          try {
            dragCard.setPointerCapture(pointerId);
          } catch (err) {
            // Ignore pointer capture errors.
          }
        }
      });

      document.addEventListener("pointermove", handlePointerMove);
      document.addEventListener("pointerup", (event) => {
        finishPointerDrag(event, false);
      });
      document.addEventListener("pointercancel", (event) => {
        finishPointerDrag(event, true);
      });
    } else {
      document.addEventListener("dragstart", (event) => {
        const card = event.target.closest('[data-task-card][draggable="true"]');
        if (!card || !isWithinTasksBoard(card)) return;
        dragCard = card;
        dragOrigin = {
          body: card.closest("[data-tasks-column-body]"),
          nextSibling: card.nextElementSibling,
          when: card.dataset.taskWhen || "today",
          project: card.dataset.taskProjectId || "",
        };
        taskDragInProgress = true;
        card.classList.add("is-dragging");
        setGlobalDragging(true);
        placeholder.style.height = `${card.offsetHeight}px`;
        logDrag(`task dragstart ${card.dataset.taskId || ""}`);
        if (event.dataTransfer) {
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", card.dataset.taskId || "");
        }
      });

      document.addEventListener("dragend", () => {
        if (!dragCard) return;
        logDrag("task dragend");
        setGlobalDragging(false);
        if (!dropHandled) {
          placeholder.remove();
          updateColumnCounts();
          updateEmptyStates();
        }
        finalizeDrag();
      });

      document.addEventListener("dragover", (event) => {
        if (!dragCard) return;
        const column = event.target.closest("[data-tasks-column]");
        if (!column || !isWithinTasksBoard(column)) return;
        const body =
          event.target.closest("[data-tasks-column-body]") ||
          column.querySelector("[data-tasks-column-body]");
        if (!body) return;
        event.preventDefault();
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = "move";
        }
        clearDropTargets();
        column.classList.add("is-drop-target");
        const after = getAfterElement(body, event.clientY);
        if (!after) {
          body.appendChild(placeholder);
        } else {
          body.insertBefore(placeholder, after);
        }
        if (dropColumn !== column) {
          logDrag(
            `task dragover ${column.dataset.whenBucket || column.dataset.projectId || ""}`
          );
        }
        dropBody = body;
        dropColumn = column;
      });

      document.addEventListener("drop", async (event) => {
        if (!dragCard) return;
        const column =
          event.target.closest("[data-tasks-column]") ||
          (dropColumn && isWithinTasksBoard(dropColumn) ? dropColumn : null);
        if (!column) {
          placeholder.remove();
          finalizeDrag();
          return;
        }
        const body =
          (dropBody && column.contains(dropBody) && dropBody) ||
          column.querySelector("[data-tasks-column-body]");
        if (!body) {
          placeholder.remove();
          finalizeDrag();
          return;
        }
        event.preventDefault();
        clearDropTargets();
        dropHandled = true;
        logDrag("task drop");
        await commitMove(column, body);
      });
    }
  }

  const horizonBoard = document.querySelector("[data-horizon-board]");
  if (horizonBoard) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
    const usePointerDrag = isTauriEnv;

    let dragInfo = null;
    const longRangeError = (message) =>
      showToast(message || "Unable to update horizon. Try again.", { variant: "error" });

    const postProjectHorizon = async (projectId, targetKey) => {
      if (!csrfToken) {
        return { ok: false, detail: "Missing CSRF token. Refresh and try again." };
      }
      if (!projectId || !targetKey) {
        return { ok: false, detail: "Missing project or horizon target." };
      }
      const formData = new FormData();
      formData.append("csrf_token", csrfToken);
      formData.append("time_horizon", targetKey);

      try {
        const response = await fetch(`/long-term/projects/${projectId}/horizon`, {
          method: "POST",
          body: formData,
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          return { ok: false, detail: detail.detail || "Unable to update horizon. Try again." };
        }
        return { ok: true };
      } catch (err) {
        return {
          ok: false,
          detail: "Unable to update horizon. Check your connection and try again.",
        };
      }
    };

    const clearDropTargets = () => {
      horizonBoard
        .querySelectorAll(".is-drop-target")
        .forEach((el) => el.classList.remove("is-drop-target"));
    };

    const refreshHorizonCount = (column) => {
      if (!column) return;
      const list = column.querySelector("[data-horizon-list]");
      const countPill = column.querySelector(".horizon-header .pill");
      if (!list || !countPill) return;
      const count = list.querySelectorAll("[data-project-id]").length;
      countPill.textContent = String(count);
    };

    const refreshHorizonCounts = (...columns) => {
      const seen = new Set();
      columns.forEach((column) => {
        if (!column || seen.has(column)) return;
        seen.add(column);
        refreshHorizonCount(column);
      });
    };

    horizonBoard.querySelectorAll("[data-project-id]").forEach((item) => {
      if (usePointerDrag) {
        item.removeAttribute("draggable");
      } else {
        item.setAttribute("draggable", "true");
      }
    });

    if (usePointerDrag) {
      const placeholder = document.createElement("div");
      placeholder.className = "horizon-drop-placeholder";
      placeholder.setAttribute("aria-hidden", "true");
      let dragItem = null;
      let dragOrigin = null;
      let dropColumn = null;
      let dropList = null;
      let dragging = false;
      let pointerId = null;
      let startX = 0;
      let startY = 0;
      let ghostOffsetX = 0;
      let ghostOffsetY = 0;
      let dragItemStyle = "";
      const dragCursorOffsetY = 15;
      const dragThreshold = 6;

      const getColumnFromPoint = (x, y) => {
        const columns = horizonBoard.querySelectorAll("[data-horizon-column]");
        for (const column of columns) {
          const rect = column.getBoundingClientRect();
          if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
            return column;
          }
        }
        return null;
      };

      const shouldIgnorePointer = (event) =>
        Boolean(event.target.closest("input, textarea, select, button, a"));

      const resetPointer = () => {
        dragging = false;
        pointerId = null;
        startX = 0;
        startY = 0;
        ghostOffsetX = 0;
        ghostOffsetY = 0;
        dragItemStyle = "";
      };

      const restoreDraggedItem = () => {
        if (!dragItem) return;
        dragItem.classList.remove("drag-lift");
        if (dragItemStyle) {
          dragItem.setAttribute("style", dragItemStyle);
        } else {
          dragItem.removeAttribute("style");
        }
      };

      const updateGhostPosition = (event) => {
        if (!dragItem || !dragging) return;
        dragItem.style.left = `${event.clientX - ghostOffsetX}px`;
        dragItem.style.top = `${event.clientY - ghostOffsetY}px`;
      };

      const beginDrag = (event) => {
        if (!dragItem || !event) return;
        dragging = true;
        horizonDragInProgress = true;
        dragItem.classList.add("is-dragging");
        dragItem.classList.add("drag-lift");
        setGlobalDragging(true);
        const rect = dragItem.getBoundingClientRect();
        placeholder.style.height = `${rect.height}px`;
        placeholder.style.width = `${rect.width}px`;
        placeholder.style.display = window.getComputedStyle(dragItem).display;
        if (dragOrigin?.list) {
          dragOrigin.list.insertBefore(placeholder, dragItem);
        }
        dragItemStyle = dragItem.getAttribute("style") || "";
        ghostOffsetX = event.clientX - rect.left;
        ghostOffsetY = event.clientY - rect.top + dragCursorOffsetY;
        document.body.appendChild(dragItem);
        dragItem.style.position = "fixed";
        dragItem.style.width = `${rect.width}px`;
        dragItem.style.height = `${rect.height}px`;
        dragItem.style.left = `${rect.left}px`;
        dragItem.style.top = `${rect.top}px`;
        dragItem.style.pointerEvents = "none";
        updateGhostPosition(event);
        logDrag(`horizon dragstart ${dragItem.dataset.projectId || ""}`);
      };

      const revertToOrigin = () => {
        if (!dragOrigin?.list || !dragItem) return;
        if (dragOrigin.nextSibling) {
          dragOrigin.list.insertBefore(dragItem, dragOrigin.nextSibling);
        } else {
          dragOrigin.list.appendChild(dragItem);
        }
      };

      const handlePointerMove = (event) => {
        if (!dragItem || pointerId !== event.pointerId) return;
        const dx = event.clientX - startX;
        const dy = event.clientY - startY;
        if (!dragging) {
          if (Math.hypot(dx, dy) < dragThreshold) return;
          beginDrag(event);
        }
        event.preventDefault();
        updateGhostPosition(event);
        const target =
          event.target.closest?.("[data-horizon-column]") ||
          getColumnFromPoint(event.clientX, event.clientY);
        if (!target) {
          clearDropTargets();
          dropColumn = null;
          dropList = null;
          placeholder.remove();
          return;
        }
        const list = target.querySelector("[data-horizon-list]");
        if (!list) return;
        clearDropTargets();
        target.classList.add("is-drop-target");
        if (placeholder.parentNode !== list) {
          list.appendChild(placeholder);
        }
        dropColumn = target;
        dropList = list;
      };

      const finishPointerDrag = async (event, cancelled = false) => {
        if (!dragItem || pointerId !== event.pointerId) return;
        if (dragItem.releasePointerCapture) {
          try {
            dragItem.releasePointerCapture(pointerId);
          } catch (err) {
            // Ignore pointer capture release errors.
          }
        }
        if (!dragging) {
          dragItem = null;
          dragOrigin = null;
          resetPointer();
          setGlobalDragging(false);
          return;
        }
        logDrag("horizon dragend");
        if (cancelled || !dropColumn || !dropList) {
          restoreDraggedItem();
          revertToOrigin();
          placeholder.remove();
          clearDropTargets();
          dragItem?.classList.remove("is-dragging");
          dragItem = null;
          dragOrigin = null;
          resetPointer();
          setGlobalDragging(false);
          setTimeout(() => {
            horizonDragInProgress = false;
          }, 80);
          return;
        }

        const targetKey = dropColumn.dataset.horizonKey;
        const sourceColumn = dragOrigin?.column || null;
        if (!targetKey || targetKey === dragOrigin?.sourceKey) {
          restoreDraggedItem();
          revertToOrigin();
          placeholder.remove();
          clearDropTargets();
          dragItem?.classList.remove("is-dragging");
          dragItem = null;
          dragOrigin = null;
          resetPointer();
          setGlobalDragging(false);
          setTimeout(() => {
            horizonDragInProgress = false;
          }, 80);
          return;
        }

        if (placeholder.parentNode === dropList) {
          dropList.insertBefore(dragItem, placeholder);
        } else {
          dropList.appendChild(dragItem);
        }
        placeholder.remove();
        restoreDraggedItem();
        dragItem.classList.remove("is-dragging");
        refreshHorizonCounts(sourceColumn, dropColumn);

        try {
          const result = await postProjectHorizon(dragOrigin?.projectId, targetKey);
          if (!result.ok) {
            longRangeError(result.detail);
            revertToOrigin();
            refreshHorizonCounts(sourceColumn, dropColumn);
            return;
          }
          showToast("Project horizon updated.", { variant: "success", timeout: 2400 });
        } finally {
          dragItem = null;
          dragOrigin = null;
          resetPointer();
          setGlobalDragging(false);
          clearDropTargets();
          setTimeout(() => {
            horizonDragInProgress = false;
          }, 80);
        }
      };

      horizonBoard.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || event.isPrimary === false) return;
        if (shouldIgnorePointer(event)) return;
        const item = event.target.closest("[data-project-id]");
        if (!item || !horizonBoard.contains(item)) return;
        const column = item.closest("[data-horizon-column]");
        const list = column?.querySelector("[data-horizon-list]");
        if (!column || !list) return;
        dragItem = item;
        dragOrigin = {
          column,
          list,
          nextSibling: item.nextElementSibling,
          sourceKey: column.dataset.horizonKey,
          projectId: item.dataset.projectId,
        };
        dropColumn = null;
        dropList = null;
        pointerId = event.pointerId;
        startX = event.clientX;
        startY = event.clientY;
        if (dragItem.setPointerCapture) {
          try {
            dragItem.setPointerCapture(pointerId);
          } catch (err) {
            // Ignore pointer capture errors.
          }
        }
      });

      document.addEventListener("pointermove", handlePointerMove);
      document.addEventListener("pointerup", (event) => {
        finishPointerDrag(event, false);
      });
      document.addEventListener("pointercancel", (event) => {
        finishPointerDrag(event, true);
      });
    } else {
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
        horizonDragInProgress = true;
        item.classList.add("is-dragging");
        setGlobalDragging(true);
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", item.dataset.projectId || "");
      });

      horizonBoard.addEventListener("dragend", () => {
        if (dragInfo?.item) {
          dragInfo.item.classList.remove("is-dragging");
        }
        dragInfo = null;
        clearDropTargets();
        setGlobalDragging(false);
        setTimeout(() => {
          horizonDragInProgress = false;
        }, 80);
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
        const targetList = column.querySelector("[data-horizon-list]");
        const item = dragInfo.item;
        const sourceColumn = item?.closest("[data-horizon-column]") || null;
        const targetKey = column.dataset.horizonKey;
        if (!targetKey || targetKey === dragInfo.sourceKey) {
          dragInfo.item.classList.remove("is-dragging");
          dragInfo = null;
          return;
        }
        const result = await postProjectHorizon(dragInfo.projectId, targetKey);
        if (!result.ok) {
          longRangeError(result.detail);
          return;
        }
        if (targetList && item && item.parentElement !== targetList) {
          targetList.appendChild(item);
        }
        refreshHorizonCounts(sourceColumn, column);
        showToast("Project horizon updated.", { variant: "success", timeout: 2400 });
      });
    }
  }

  const draggableLists = document.querySelectorAll("[data-draggable-list]");
  if (draggableLists.length) {
    const usePointerDrag = isTauriEnv;
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
      if (list.dataset.dragReady === "true") return;
      list.dataset.dragReady = "true";
      const isInboxList = list.querySelector("[data-inbox-item]") !== null;
      const placeholder = document.createElement("div");
      placeholder.className = "list-item list-placeholder";
      placeholder.setAttribute("aria-hidden", "true");
      let dragItem = null;
      let pointerId = null;
      let startX = 0;
      let startY = 0;
      let dragging = false;
      let dragItemStyle = "";
      let ghostOffsetX = 0;
      let ghostOffsetY = 0;
      const dragCursorOffsetY = 80;

      list.querySelectorAll(".list-item").forEach((item) => {
        if (usePointerDrag) {
          item.removeAttribute("draggable");
        } else {
          item.setAttribute("draggable", "true");
        }
      });

      if (usePointerDrag) {
        const dragThreshold = 6;
        const shouldIgnorePointer = (event) =>
          Boolean(
            event.target.closest("[data-inbox-action], button, a, input, textarea, select")
          );

        const resetPointer = () => {
          pointerId = null;
          startX = 0;
          startY = 0;
          dragging = false;
          ghostOffsetX = 0;
          ghostOffsetY = 0;
          dragItemStyle = "";
        };

        const updateGhostPosition = (event) => {
          if (!dragItem || !dragging) return;
          dragItem.style.left = `${event.clientX - ghostOffsetX}px`;
          dragItem.style.top = `${event.clientY - ghostOffsetY}px`;
        };

        const beginDrag = (event) => {
          if (!dragItem || !event) return;
          dragging = true;
          dragItem.classList.add("dragging");
          dragItem.classList.add("drag-lift");
          setGlobalDragging(true);
          placeholder.style.height = `${dragItem.offsetHeight}px`;
          list.insertBefore(placeholder, dragItem);
          dragItemStyle = dragItem.getAttribute("style") || "";
          const rect = dragItem.getBoundingClientRect();
          ghostOffsetX = event.clientX - rect.left;
          ghostOffsetY = event.clientY - rect.top + dragCursorOffsetY;
          document.body.appendChild(dragItem);
          dragItem.style.position = "fixed";
          dragItem.style.width = `${rect.width}px`;
          dragItem.style.height = `${rect.height}px`;
          dragItem.style.left = `${rect.left}px`;
          dragItem.style.top = `${rect.top}px`;
          dragItem.style.pointerEvents = "none";
          updateGhostPosition(event);
          if (isInboxList) inboxDragInProgress = true;
          logDrag(
            `${isInboxList ? "inbox" : "list"} dragstart ${dragItem.dataset.taskId || ""}`
          );
        };

        const handlePointerMove = (event) => {
          if (!dragItem || pointerId !== event.pointerId) return;
          const dx = event.clientX - startX;
          const dy = event.clientY - startY;
          if (!dragging) {
            if (Math.hypot(dx, dy) < dragThreshold) return;
            beginDrag(event);
          }
          event.preventDefault();
          updateGhostPosition(event);
          const rect = list.getBoundingClientRect();
          const inside =
            event.clientX >= rect.left &&
            event.clientX <= rect.right &&
            event.clientY >= rect.top &&
            event.clientY <= rect.bottom;
          if (!inside) {
            placeholder.remove();
            return;
          }
          const after = getAfterElement(list, event.clientY);
          if (!after) {
            list.appendChild(placeholder);
          } else {
            list.insertBefore(placeholder, after);
          }
        };

        const finishPointerDrag = (event, cancelled = false) => {
          if (!dragItem || pointerId !== event.pointerId) return;
          if (dragItem.releasePointerCapture) {
            try {
              dragItem.releasePointerCapture(pointerId);
            } catch (err) {
              // Ignore pointer capture release errors.
            }
          }
          if (!dragging) {
            dragItem = null;
            resetPointer();
            setGlobalDragging(false);
            return;
          }
          dragItem.classList.remove("drag-lift");
          if (dragItemStyle) {
            dragItem.setAttribute("style", dragItemStyle);
          } else {
            dragItem.removeAttribute("style");
          }
          logDrag(`${isInboxList ? "inbox" : "list"} dragend`);
          if (!cancelled) {
            if (placeholder.parentNode === list) {
              list.insertBefore(dragItem, placeholder);
            } else {
              list.appendChild(dragItem);
            }
            logDrag(`${isInboxList ? "inbox" : "list"} drop`);
          }
          placeholder.remove();
          dragItem.classList.remove("dragging");
          dragItem = null;
          setGlobalDragging(false);
          if (isInboxList) {
            setTimeout(() => {
              inboxDragInProgress = false;
            }, 80);
          }
          resetPointer();
        };

        list.addEventListener("pointerdown", (event) => {
          if (event.button !== 0 || event.isPrimary === false) return;
          if (shouldIgnorePointer(event)) return;
          const item = event.target.closest(".list-item");
          if (!item || !list.contains(item)) return;
          dragItem = item;
          pointerId = event.pointerId;
          startX = event.clientX;
          startY = event.clientY;
          if (dragItem.setPointerCapture) {
            try {
              dragItem.setPointerCapture(pointerId);
            } catch (err) {
              // Ignore pointer capture errors.
            }
          }
        });

        document.addEventListener("pointermove", handlePointerMove);
        document.addEventListener("pointerup", (event) => {
          finishPointerDrag(event, false);
        });
        document.addEventListener("pointercancel", (event) => {
          finishPointerDrag(event, true);
        });
      } else {
        document.addEventListener("dragstart", (event) => {
          const item = event.target.closest(".list-item");
          if (!item || !list.contains(item)) return;
          dragItem = item;
          item.classList.add("dragging");
          setGlobalDragging(true);
          placeholder.style.height = `${item.offsetHeight}px`;
          if (isInboxList) inboxDragInProgress = true;
          logDrag(
            `${isInboxList ? "inbox" : "list"} dragstart ${item.dataset.taskId || ""}`
          );
          if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", item.dataset.taskId || "");
          }
        });

        document.addEventListener("dragend", () => {
          if (!dragItem) return;
          logDrag(`${isInboxList ? "inbox" : "list"} dragend`);
          setGlobalDragging(false);
          dragItem.classList.remove("dragging");
          placeholder.remove();
          dragItem = null;
          if (isInboxList) {
            setTimeout(() => {
              inboxDragInProgress = false;
            }, 80);
          }
        });

        document.addEventListener("dragover", (event) => {
          if (!dragItem) return;
          const targetList = event.target.closest("[data-draggable-list]");
          if (!targetList || targetList !== list) return;
          event.preventDefault();
          if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
          }
          const after = getAfterElement(targetList, event.clientY);
          if (!after) {
            targetList.appendChild(placeholder);
          } else {
            targetList.insertBefore(placeholder, after);
          }
        });

        document.addEventListener("drop", (event) => {
          if (!dragItem) return;
          const targetList = event.target.closest("[data-draggable-list]");
          if (!targetList || targetList !== list) return;
          event.preventDefault();
          if (placeholder.parentNode === targetList) {
            targetList.insertBefore(dragItem, placeholder);
          } else {
            targetList.appendChild(dragItem);
          }
          placeholder.remove();
          dragItem.classList.remove("dragging");
          dragItem = null;
          logDrag(`${isInboxList ? "inbox" : "list"} drop`);
          if (isInboxList) {
            setTimeout(() => {
              inboxDragInProgress = false;
            }, 80);
          }
        });
      }
    });
  }

  if (typeof window.initCoachWidget === "function") {
    window.initCoachWidget({ showToast, isTauriEnv });
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
