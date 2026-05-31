import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const indexHtmlPath = new URL("./index.html", import.meta.url);
const clientJsPath = new URL("./client.js", import.meta.url);
const launcherJsPath = new URL("./launcher.js", import.meta.url);
const launcherCssPath = new URL("./launcher.css", import.meta.url);

test("launcher exposes the five top-level workflows", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  for (const workflow of ["today", "capture", "process", "review", "settings"]) {
    assert.match(indexHtml, new RegExp(`data-workflow-tab="${workflow}"`));
    assert.match(indexHtml, new RegExp(`data-workflow-panel="${workflow}"`));
  }

  assert.match(indexHtml, /<nav class="workflow-nav"/);
  assert.match(indexHtml, /<h2>Today<\/h2>/);
  assert.doesNotMatch(indexHtml, /Home \/ Today/);
  assert.match(indexHtml, /Today/);
  assert.match(indexHtml, /Capture/);
  assert.match(indexHtml, /Process/);
  assert.match(indexHtml, /Review/);
  assert.match(indexHtml, /Settings/);
});

test("launcher keeps Settings compact on phone without losing accessibility", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  assert.match(indexHtml, /data-workflow-tab="settings"[^>]*aria-label="Settings"/);
  assert.match(indexHtml, /class="workflow-tab-mobile-icon"[^>]*aria-hidden="true"[^>]*>&#9881;<\/span>/);
});

test("connection settings are scoped to the Settings workflow", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const settingsPanelStart = indexHtml.indexOf('data-workflow-panel="settings"');
  const connectionCard = indexHtml.indexOf('id="connection-card"');

  assert.ok(settingsPanelStart >= 0, "settings workflow exists");
  assert.ok(connectionCard > settingsPanelStart, "connection card lives inside settings");
});

test("launcher exposes persistent global search in the header", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const clientJs = readFileSync(clientJsPath, "utf8");
  const launcherJs = readFileSync(launcherJsPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(indexHtml, /id="global-search-input"/);
  assert.match(indexHtml, /id="global-search-include-recycle"/);
  assert.match(indexHtml, /id="global-search-results"/);
  assert.match(launcherJs, /buildSearchApiPath/);
  assert.match(launcherJs, /performGlobalSearch/);
  assert.match(clientJs, /\/api\/v1\/search/);
  assert.match(launcherJs, /data-search-result-workflow/);
  assert.match(launcherCss, /\.global-search/);
  assert.match(launcherCss, /\.search-results-panel/);
});

test("launcher keeps recycle-bin search behind collapsed options", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(indexHtml, /<details class="global-search-options"/);
  assert.match(indexHtml, /<summary>Search options<\/summary>/);
  assert.match(indexHtml, /id="global-search-include-recycle"/);
  assert.match(launcherCss, /\.global-search-options/);
  assert.match(launcherCss, /\.global-search-options\[open\]/);
});

test("launcher exposes an item detail drawer for search results", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const clientJs = readFileSync(clientJsPath, "utf8");
  const launcherJs = readFileSync(launcherJsPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(indexHtml, /id="item-detail-drawer"/);
  assert.match(indexHtml, /id="item-detail-title"/);
  assert.match(indexHtml, /id="item-detail-load-state"/);
  assert.match(indexHtml, /id="item-detail-actions"/);
  assert.match(indexHtml, /id="item-detail-edit-form"/);
  assert.match(clientJs, /buildItemDetailViewModel/);
  assert.match(clientJs, /buildItemDetailApiPath/);
  assert.match(clientJs, /buildItemDetailActions/);
  assert.match(clientJs, /buildItemDetailUpdatePayload/);
  assert.match(launcherJs, /openItemDetail/);
  assert.match(launcherJs, /loadItemDetail/);
  assert.match(launcherJs, /performItemDetailAction/);
  assert.match(launcherJs, /saveItemDetailEdit/);
  assert.match(launcherJs, /openProjectShapeCard/);
  assert.match(launcherJs, /requestJson\(window\.fetch\.bind\(window\), settings, path\)/);
  assert.match(launcherJs, /data-item-detail-action-id/);
  assert.match(launcherJs, /searchResultKind/);
  assert.match(launcherJs, /itemDetailOpen/);
  assert.match(launcherCss, /\.item-detail-drawer/);
  assert.match(launcherCss, /\.item-detail-edit/);
  assert.match(launcherCss, /\.item-detail-backdrop/);
});

test("launcher makes normal task and project rows open item details", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherJs, /attachItemDetail/);
  assert.match(launcherJs, /data-item-detail/);
  assert.match(launcherJs, /itemDetailFromElement/);
  assert.match(launcherJs, /closest\("\[data-item-detail\]"\)/);
  assert.match(launcherJs, /isItemDetailInteractiveTarget/);
  assert.match(launcherCss, /\.has-item-detail/);
});

test("launcher wires workflow navigation state", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /querySelectorAll\("\[data-workflow-tab\]"\)/);
  assert.match(launcherJs, /querySelectorAll\("\[data-workflow-panel\]"\)/);
  assert.match(launcherJs, /function setWorkflow\(/);
  assert.match(launcherJs, /document\.body\.dataset\.workflow/);
  assert.match(launcherJs, /tab\.addEventListener\("click"/);
});

test("launcher uses workflow-specific capture and process models", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /buildCaptureWorkflowViewModel/);
  assert.match(launcherJs, /buildProcessWorkflowViewModel/);
  assert.match(launcherJs, /renderTodayTasks/);
  assert.match(launcherJs, /processPosition/);
  assert.match(launcherJs, /setWorkflow\("settings"\)/);
});

test("process workflow reserves a dedicated current-decision panel", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(indexHtml, /id="process-active-heading"/);
  assert.match(indexHtml, /id="process-active-item"/);
  assert.match(indexHtml, /Current item/);
  assert.match(indexHtml, /id="process-active-actions"/);
  assert.match(launcherJs, /processActiveHeading/);
  assert.match(launcherJs, /processActiveItem/);
  assert.match(launcherJs, /processActiveActions/);
});

test("process inbox card renders only the unresolved inbox total", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /elements\.inboxTotal\.textContent = String\(model\.inboxTotal\);/);
  assert.match(launcherJs, /elements\.inboxCounts\.replaceChildren\(\);/);
  assert.doesNotMatch(launcherJs, /countPill\("Learning"/);
  assert.doesNotMatch(launcherJs, /countPill\("Enjoy"/);
  assert.doesNotMatch(launcherJs, /countPill\("Parked"/);
  assert.doesNotMatch(launcherJs, /countPill\("Recycle"/);
});

test("launcher wires Today task complete and reopen actions", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /data-today-task-action/);
  assert.match(launcherJs, /buildTodayTaskActionFeedback/);
  assert.match(launcherJs, /todayTasks\.addEventListener\("click"/);
  assert.match(launcherJs, /\/api\/v1\/tasks\/\$\{encodeURIComponent\(taskId\)\}\/\$\{action\}/);
});

test("launcher clears stale action feedback before reconnecting", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /function clearActionFeedback\(\)/);
  assert.match(
    launcherJs,
    /async function connectAndLoad\(options = \{\}\) \{\n\s+clearActionFeedback\(\);/,
  );
});

test("launcher retries startup connection when the server is not ready yet", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /const STARTUP_CONNECT_RETRY_MS = 1000;/);
  assert.match(launcherJs, /const STARTUP_CONNECT_MAX_ATTEMPTS = 30;/);
  assert.match(launcherJs, /async function connectAndLoad\(options = \{\}\)/);
  assert.match(launcherJs, /scheduleStartupReconnect\(\);/);
  assert.match(launcherJs, /startupReconnectAttempts >= STARTUP_CONNECT_MAX_ATTEMPTS/);
  assert.match(launcherJs, /window\.setTimeout\(\(\) => \{/);
});

test("launcher wakes itself when parked-until items become due", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /nextParkedItemRefreshDelay/);
  assert.match(launcherJs, /let parkResurfaceTimer = null;/);
  assert.match(launcherJs, /function scheduleParkResurfaceRefresh\(inboxContainers\)/);
  assert.match(launcherJs, /scheduleParkResurfaceRefresh\(inboxContainers\);/);
  assert.match(launcherJs, /window\.setTimeout\(async \(\) => \{/);
  assert.match(launcherJs, /await refreshWorkflowData\(activeWorkflow\);/);
});

test("launcher clears action feedback when switching workflows", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(
    launcherJs,
    /tab\.addEventListener\("click", async \(\) => \{\n\s+const nextWorkflow = tab\.dataset\.workflowTab;\n\s+clearActionFeedback\(\);\n\s+setWorkflow\(nextWorkflow\);/,
  );
});

test("launcher refreshes shared server data when switching data-backed workflows", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /async function refreshWorkflowData\(workflow\)/);
  assert.match(launcherJs, /if \(\["today", "capture", "process"\]\.includes\(workflow\)\)/);
  assert.match(launcherJs, /await refreshDashboardAndProcess\(\);/);
  assert.match(launcherJs, /await refreshWorkflowData\(nextWorkflow\);/);
});

test("launcher renders guided process as progressive steps", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /guidedProcessStepPlan/);
  assert.match(launcherJs, /function guidedStepSection\(/);
  assert.match(launcherJs, /dataset\.guidedStep/);
  assert.match(launcherJs, /function setGuidedStep\(/);
  assert.match(launcherJs, /data-guided-action/);
});

test("launcher starts Process clarification with a compact choice", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /summary\.textContent = "Make this a task"/);
  assert.match(launcherJs, /legend\.textContent = "What is this\?"/);
  assert.match(launcherJs, /decisionHelpDetails\(\)/);
  assert.match(launcherJs, /summary\.textContent = "Help me choose"/);
  assert.match(launcherJs, /for \(const \[value, labelText\] of DECISION_OPTIONS\)/);
  assert.doesNotMatch(launcherJs, /Step 1 · choose the right kind of follow-up/);
  assert.doesNotMatch(launcherJs, /decisionCopyPanel\(\),/);
});

test("guided process cards preserve sentence-case explanatory text", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /\.decision-card-body\s*\{[\s\S]*letter-spacing:\s*0;[\s\S]*text-transform:\s*none;/,
  );
  assert.match(
    launcherCss,
    /\.decision-card-body small\s*\{[\s\S]*text-transform:\s*none;/,
  );
});

test("launcher makes Park an explicit optional date-time choice", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherJs, /parkChoicePanel/);
  assert.match(launcherJs, /park-menu/);
  assert.match(launcherJs, /data-park-action|dataset\.parkAction/);
  assert.match(launcherJs, /Park without date/);
  assert.match(launcherJs, /Park until date\/time/);
  assert.match(launcherJs, /buildParkRoutePayload/);
  assert.match(launcherJs, /parkCalendarControl/);
  assert.match(launcherJs, /data-park-calendar-action/);
  assert.doesNotMatch(launcherJs, /datetime-local/);
  assert.match(launcherCss, /\.park-choice-panel/);
  assert.match(launcherCss, /\.park-calendar-day/);
  assert.match(launcherCss, /min-height:\s*56px/);
});

test("launcher formats parked feedback and lets it dismiss itself", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherJs, /const ACTION_FEEDBACK_DISMISS_MS = 30000;/);
  assert.match(launcherJs, /let actionFeedbackDismissTimer = null;/);
  assert.match(launcherJs, /function scheduleActionFeedbackDismiss\(\)/);
  assert.match(launcherJs, /function hideActionFeedbackWithTransition\(\)/);
  assert.match(launcherJs, /formatParkedUntilFeedbackLabel\(parkedUntilValue\)/);
  assert.match(launcherJs, /function formatParkedUntilFeedbackLabel\(value\)/);
  assert.doesNotMatch(launcherJs, /parkedUntilValue\.replace\("T", " "\)/);
  assert.match(launcherCss, /\.action-feedback\s*\{[\s\S]*transition:/);
  assert.match(launcherCss, /\.action-feedback\.is-dismissing/);
});

test("process workflow copy explains the active item before clarification", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherJs = readFileSync(launcherJsPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(indexHtml, /To Process/);
  assert.match(indexHtml, /Most likely/);
  assert.match(indexHtml, /Change to Project or Waiting On if needed\./);
  assert.match(
    indexHtml,
    /class="process-layout"[\s\S]*class="panel process-active-panel"[\s\S]*class="panel inbox-processing-panel"[\s\S]*class="panel inbox-panel"/,
  );
  assert.match(indexHtml, /id="inbox-items"[\s\S]*id="process-active-actions"/);
  assert.doesNotMatch(indexHtml, /class="panel wide-panel inbox-processing-panel"/);
  assert.match(
    launcherCss,
    /#workflow-process \.inbox-panel\s*\{[\s\S]*display:\s*none/,
  );
  assert.match(
    launcherCss,
    /#workflow-process \.inbox-processing-panel\s*\{[\s\S]*grid-column:\s*auto/,
  );
  assert.match(
    launcherCss,
    /\.process-active-actions\s*\{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*repeat\(4, minmax\(0, 1fr\)\)/,
  );
  assert.match(
    launcherCss,
    /#workflow-process > \.section-heading h2\s*\{[\s\S]*font-size:\s*var\(--sfo-workflow-title-size\)/,
  );
  assert.match(
    launcherCss,
    /\.process-active-title\s*\{[\s\S]*font-size:\s*var\(--sfo-current-item-title-size\)/,
  );
  assert.match(
    launcherCss,
    /\.process-next-step-title\s*\{[\s\S]*font-size:\s*var\(--sfo-quiet-heading-size\)/,
  );
  assert.match(launcherJs, /elements\.processActiveHeading\.textContent = item\.title/);
  assert.match(launcherJs, /learn_explore: "Learn"/);
  assert.match(launcherJs, /recycle\.textContent = "♻"/);
  assert.doesNotMatch(indexHtml, /Process next item/);
  assert.doesNotMatch(indexHtml, /Choose what happens to the current inbox item/);
  assert.doesNotMatch(indexHtml, /Choose what happens to this item\./);
  assert.doesNotMatch(indexHtml, /Start with a quick route/);
  assert.doesNotMatch(indexHtml, /Decision Queue/);
  assert.doesNotMatch(indexHtml, /One item at a time\./);
});

test("launcher wires weekly review actions", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  assert.match(launcherJs, /buildWeeklyReviewViewModel/);
  assert.match(launcherJs, /weekly-review/);
  assert.match(launcherJs, /data-review-action/);
  assert.match(launcherJs, /move-to-week/);
  assert.match(indexHtml, /review-learning-items/);
  assert.match(indexHtml, /review-enjoy-items/);
  assert.match(indexHtml, /review-parked-items/);
  assert.match(indexHtml, /review-recycle-bin-items/);
  assert.match(indexHtml, /review-recycle-bin-count/);
  assert.match(indexHtml, /review-learning-count/);
  assert.match(launcherJs, /data-review-inbox-action/);
  assert.match(launcherJs, /restore-inbox-item/);
  assert.match(launcherJs, /recycle-inbox-item/);
  assert.match(launcherJs, /restore-recycled-item/);
  assert.match(launcherJs, /delete-recycled-item/);
  assert.match(launcherJs, /Confirm delete/);
  assert.match(launcherJs, /confirming-delete/);
  assert.match(launcherJs, /confirmResetTimer/);
  assert.match(launcherJs, /setTimeout\(\(\) => \{/);
  assert.match(launcherJs, /\/api\/v1\/tasks\/\$\{encodeURIComponent\(itemId\)\}/);
});

test("project shaping forms require finish dates and chunk titles", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /function requiredTextInput/);
  assert.ok(
    launcherJs.includes('formField("Target date", requiredTextInput("target_date"'),
    "project card target date should be required before submit",
  );
  assert.ok(
    launcherJs.includes('formField("Next chunk", requiredTextInput("verb_noun"'),
    "roadmap chunk title should be required before submit",
  );
});

test("review workflow is structured as a weekly checklist", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(indexHtml, /review-checklist/);
  assert.match(indexHtml, /Step 1/);
  assert.match(indexHtml, /Choose this week/);
  assert.match(indexHtml, /Step 2/);
  assert.match(indexHtml, /Reconsider due work/);
  assert.match(indexHtml, /Step 3/);
  assert.match(indexHtml, /Scan parked buckets/);
  assert.match(indexHtml, /Step 4/);
  assert.match(indexHtml, /Finish clean/);
  assert.match(indexHtml, /Recycle Bin/);
  assert.match(launcherCss, /\.review-panel-title/);
  assert.match(launcherCss, /\.review-list\.is-scrollable/);
  assert.match(launcherCss, /max-height:\s*340px/);
  assert.match(launcherCss, /\.review-step-grid\.three-up\s+\.review-task-row/);
  assert.match(launcherCss, /\.review-step/);
  assert.match(launcherCss, /\.review-step-grid/);
});

test("review and today date labels share the same presentation class", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  assert.match(indexHtml, /class="eyebrow workflow-date-label" id="today-label"/);
  assert.match(indexHtml, /class="eyebrow workflow-date-label" id="review-date-label"/);
});

test("today refresh keeps text label and mobile icon with accessible name", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  assert.match(indexHtml, /id="refresh-dashboard"[^>]*aria-label="Refresh Today"/);
  assert.match(indexHtml, /class="refresh-button-label">Refresh<\/span>/);
  assert.match(indexHtml, /class="refresh-button-icon"[^>]*aria-hidden="true"[^>]*>&#8635;<\/span>/);
});

test("today focus has a compact summary toggle without replacing the save form", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(indexHtml, /id="daily-focus-card"/);
  assert.match(indexHtml, /id="daily-focus-toggle"[^>]*aria-controls="daily-focus-form"/);
  assert.match(indexHtml, /id="daily-focus-one-thing-summary"/);
  assert.match(indexHtml, /id="daily-focus-frog-summary"/);
  assert.match(indexHtml, /id="daily-focus-toggle-icon"/);
  assert.match(indexHtml, /<form class="daily-focus-form" id="daily-focus-form">/);
  assert.match(launcherJs, /dailyFocusToggle: document\.getElementById\("daily-focus-toggle"\)/);
  assert.match(launcherJs, /function setDailyFocusEditing\(isEditing\)/);
  assert.match(launcherJs, /function renderDailyFocusSummary\(dailyFocus\)/);
  assert.match(launcherJs, /dailyFocusToggle\.addEventListener\("click"/);
});

test("today secondary panels have phone collapsible controls while preserving panel content", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  for (const id of ["today-context", "weekly-projects", "today-blocks"]) {
    assert.match(indexHtml, new RegExp(`id="${id}-section"`));
    assert.match(indexHtml, new RegExp(`aria-controls="${id}-content"`));
    assert.match(indexHtml, new RegExp(`id="${id}-content"`));
  }

  assert.match(indexHtml, /class="panel today-tasks-panel"/);
  assert.match(indexHtml, /data-today-secondary-section/);
  assert.match(indexHtml, /data-today-secondary-toggle/);
  assert.match(indexHtml, /class="today-secondary-toggle-icon"[^>]*>\+<\/span>/);
  assert.match(launcherJs, /todaySecondaryToggles: \[\.\.\.document\.querySelectorAll\("\[data-today-secondary-toggle\]"\)\]/);
  assert.match(launcherJs, /function setTodaySecondarySection\(section, isOpen\)/);
  assert.match(launcherJs, /todaySecondaryToggles\) \{/);
});
