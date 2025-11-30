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
  const updateClock = () => {
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
  };
  updateClock();
  setInterval(updateClock, 1000);
});
