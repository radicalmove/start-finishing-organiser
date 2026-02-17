(() => {
  const root = document.querySelector("[data-training-live]");
  if (!root) return;

  const counterLabel = root.querySelector("[data-live-counter]");
  const addSetBtn = root.querySelector("[data-counter-add-set]");
  const addRepBtn = root.querySelector("[data-counter-add-rep]");
  const resetCounterBtn = root.querySelector("[data-counter-reset]");
  let setCount = 0;
  let repCount = 0;

  const renderCounter = () => {
    if (!counterLabel) return;
    counterLabel.textContent = `${setCount} sets / ${repCount} reps`;
  };
  if (addSetBtn) {
    addSetBtn.addEventListener("click", () => {
      setCount += 1;
      renderCounter();
    });
  }
  if (addRepBtn) {
    addRepBtn.addEventListener("click", () => {
      repCount += 1;
      renderCounter();
    });
  }
  if (resetCounterBtn) {
    resetCounterBtn.addEventListener("click", () => {
      setCount = 0;
      repCount = 0;
      renderCounter();
    });
  }
  renderCounter();

  const timerLabel = root.querySelector("[data-live-timer]");
  const restSecondsInput = root.querySelector("[data-rest-seconds]");
  const startTimerBtn = root.querySelector("[data-rest-start]");
  const resetTimerBtn = root.querySelector("[data-rest-reset]");
  let interval = null;
  let remaining = 90;
  let running = false;

  const formatClock = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  const readInitialSeconds = () => {
    const parsed = parseInt(restSecondsInput?.value || "90", 10);
    if (Number.isNaN(parsed) || parsed <= 0) return 90;
    return parsed;
  };

  const renderTimer = () => {
    if (!timerLabel) return;
    timerLabel.textContent = formatClock(remaining);
  };

  const stopTimer = () => {
    running = false;
    if (interval) {
      window.clearInterval(interval);
      interval = null;
    }
    if (startTimerBtn) startTimerBtn.textContent = "Start";
  };

  const startTimer = () => {
    if (running) {
      stopTimer();
      return;
    }
    running = true;
    if (startTimerBtn) startTimerBtn.textContent = "Pause";
    interval = window.setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        remaining = 0;
        renderTimer();
        stopTimer();
        return;
      }
      renderTimer();
    }, 1000);
  };

  remaining = readInitialSeconds();
  renderTimer();

  if (startTimerBtn) {
    startTimerBtn.addEventListener("click", startTimer);
  }
  if (resetTimerBtn) {
    resetTimerBtn.addEventListener("click", () => {
      stopTimer();
      remaining = readInitialSeconds();
      renderTimer();
    });
  }
  if (restSecondsInput) {
    restSecondsInput.addEventListener("change", () => {
      if (running) return;
      remaining = readInitialSeconds();
      renderTimer();
    });
  }
})();
