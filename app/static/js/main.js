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
});
