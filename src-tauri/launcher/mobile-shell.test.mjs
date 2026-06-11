import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const indexHtmlPath = new URL("./index.html", import.meta.url);
const launcherCssPath = new URL("./launcher.css", import.meta.url);
const iosInfoPlistPath = new URL("../gen/apple/sfo_iOS/Info.plist", import.meta.url);

test("mobile shell opts into iOS safe-area layout", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(indexHtml, /viewport-fit=cover/);
  assert.match(launcherCss, /env\(safe-area-inset-top/);
  assert.match(launcherCss, /body::after/);
});

test("iOS shell allows private HTTP WebView traffic for LAN and Tailnet servers", () => {
  const infoPlist = readFileSync(iosInfoPlistPath, "utf8");

  assert.match(infoPlist, /<key>NSAppTransportSecurity<\/key>/);
  assert.match(infoPlist, /<key>NSAllowsLocalNetworking<\/key>\s*<true\/>/);
  assert.match(infoPlist, /<key>NSAllowsArbitraryLoadsInWebContent<\/key>\s*<true\/>/);
});

test("mobile shell paints the full iOS viewport behind safe areas", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /--sfo-app-background:/);
  assert.match(launcherCss, /html\s*\{[\s\S]*background:\s*var\(--sfo-app-background\)/);
  assert.match(launcherCss, /body\s*\{[\s\S]*min-height:\s*100svh/);
  assert.match(launcherCss, /@supports \(min-height: 100dvh\)[\s\S]*body\s*\{[\s\S]*min-height:\s*100dvh/);
});

test("mobile shell applies phone layout to iOS WebView viewport widths", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /overflow-x:\s*hidden/);
  assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.app-header/);
  assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.workflow-nav/);
});

test("mobile shell constrains iOS visual viewport width", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /@supports \(width: 100svw\)/);
  assert.match(launcherCss, /width:\s*min\(calc\(100svw - 20px\), 680px\)/);
  assert.match(launcherCss, /\.status-card > div\s*\{[\s\S]*min-width:\s*0/);
  assert.match(launcherCss, /\.status-detail\s*\{[\s\S]*overflow-wrap:\s*anywhere/);
});

test("mobile shell has an iPhone SE width treatment", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /@media \(max-width: 430px\)/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*width:\s*min\(calc\(100vw - 12px\),\s*680px\)/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-nav\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1\.06fr\) minmax\(0,\s*1\.24fr\) minmax\(0,\s*1\.2fr\) minmax\(0,\s*1\.08fr\) minmax\(34px,\s*0\.42fr\)/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-tab\s*\{[\s\S]*font-size:\s*13px/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-tab\[data-workflow-tab="settings"\]\s*\{[\s\S]*grid-column:\s*auto/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-tab\[data-workflow-tab="settings"\] \.workflow-tab-label\s*\{[\s\S]*display:\s*none/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-tab\[data-workflow-tab="settings"\] \.workflow-tab-mobile-icon\s*\{[\s\S]*display:\s*inline/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-tab\[data-workflow-tab="settings"\] \.workflow-tab-mobile-icon\s*\{[\s\S]*font-size:\s*20px/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-panel\s*\{[\s\S]*padding:\s*12px/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.mini-button\s*\{[\s\S]*flex:\s*1 1 calc\(50% - 4px\)/);
});

test("mobile shell prevents iOS input focus zoom", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /input,\s*select,\s*textarea\s*\{[^}]*font-size:\s*16px/);
});

test("mobile process view keeps current item before clarification and hides inbox stats", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 1024px\)[\s\S]*#workflow-process \.process-active-panel\s*\{[\s\S]*order:\s*1/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 1024px\)[\s\S]*#workflow-process \.inbox-processing-panel\s*\{[\s\S]*order:\s*2/,
  );
  assert.match(launcherCss, /#workflow-process \.inbox-panel\s*\{[\s\S]*display:\s*none/);
});

test("mobile global search does not reserve desktop vertical space", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 1024px\)[\s\S]*\.global-search\s*\{[\s\S]*flex:\s*0 1 auto/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search-field input\s*\{[\s\S]*min-height:\s*44px/,
  );
});

test("mobile search options collapse to a plus button beside search", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\) 40px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search-options\s*\{[\s\S]*display:\s*contents/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search-options > summary\s*\{[\s\S]*grid-column:\s*2/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search-options > summary\s*\{[\s\S]*width:\s*40px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search-options > summary\s*\{[\s\S]*font-size:\s*0/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search-options > summary::after\s*\{[\s\S]*content:\s*"\+"/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.global-search-recycle\s*\{[\s\S]*grid-column:\s*1 \/ -1/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.search-results-panel\s*\{[\s\S]*grid-column:\s*1 \/ -1/,
  );
});

test("mobile Today header keeps refresh in the heading row", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#workflow-today \.dashboard-topline\s*\{[\s\S]*flex-direction:\s*row/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#workflow-today \.dashboard-topline\s*\{[\s\S]*align-items:\s*flex-end/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#workflow-today \.dashboard-topline\s*\{[\s\S]*margin-bottom:\s*8px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#refresh-dashboard\s*\{[\s\S]*width:\s*40px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#refresh-dashboard\s*\{[\s\S]*padding:\s*0/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#refresh-dashboard \.refresh-button-label\s*\{[\s\S]*display:\s*none/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#refresh-dashboard \.refresh-button-icon\s*\{[\s\S]*display:\s*inline/,
  );
});

test("mobile Today focus starts as a compact summary and expands only for editing", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.daily-focus-summary\s*\{[\s\S]*display:\s*grid/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.daily-focus-card:not\(\.is-editing\) \.daily-focus-form\s*\{[\s\S]*display:\s*none/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.daily-focus-card\.is-editing \.daily-focus-form\s*\{[\s\S]*display:\s*grid/,
  );
});

test("mobile Today prioritizes Now and tasks before collapsible secondary panels", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#workflow-today \.now-panel\s*\{[\s\S]*order:\s*1/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#workflow-today \.today-tasks-panel\s*\{[\s\S]*order:\s*2/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.today-secondary-toggle\s*\{[\s\S]*display:\s*grid/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.today-secondary-section:not\(\.is-open\) \.today-secondary-content\s*\{[\s\S]*display:\s*none/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.today-secondary-section\.is-open \.today-secondary-content\s*\{[\s\S]*display:\s*block/,
  );
});

test("iPhone header collapses connection status to a top-right indicator", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.status-card\s*\{[\s\S]*position:\s*absolute/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.status-card\s*\{[\s\S]*right:\s*10px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.status-card\s*\{[\s\S]*width:\s*28px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.status-card\s*\{[\s\S]*border-radius:\s*var\(--sfo-radius-sm\)/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.status-card > div:last-child\s*\{[\s\S]*clip-path:\s*inset\(50%\)/,
  );
});

test("mobile process controls stay inside iPhone SE width", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.process-active-actions\s*\{[\s\S]*grid-template-columns:\s*repeat\(4, minmax\(0, 1fr\)\)/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.process-active-actions \.mini-button\s*\{[\s\S]*font-size:\s*12px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.park-calendar-grid\s*\{[\s\S]*gap:\s*4px/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.park-calendar-day\s*\{[\s\S]*min-height:\s*44px/,
  );
});

test("mobile process shows the current item first and hides the duplicate inbox count", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*h2\s*\{[\s\S]*font-size:\s*var\(--sfo-mobile-workflow-title-size\)/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#workflow-process > \.section-heading h2\s*\{[\s\S]*font-size:\s*var\(--sfo-mobile-process-title-size\)/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.process-active-title\s*\{[\s\S]*font-size:\s*var\(--sfo-mobile-current-item-title-size\)/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.process-active-panel\s*\{[\s\S]*order:\s*1/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.inbox-processing-panel\s*\{[\s\S]*order:\s*2/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.inbox-panel\s*\{[\s\S]*display:\s*none/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*#workflow-process > \.section-heading\s*\{[\s\S]*flex-direction:\s*row/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.process-position\s*\{[\s\S]*color:\s*white/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.process-position\s*\{[\s\S]*font-size:\s*18px/,
  );
});

test("mobile park return time input stays inside the calendar card", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.park-time-field\s*\{[\s\S]*min-width:\s*0/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.park-time-field\s*\{[\s\S]*overflow:\s*hidden/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.park-time-field input\s*\{[\s\S]*max-width:\s*100%/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.park-time-field input\s*\{[\s\S]*min-width:\s*0/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.park-time-field input\s*\{[\s\S]*box-sizing:\s*border-box/,
  );
});

test("mobile process clarification hides secondary chrome on the first choice", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.guided-form\[data-guided-step="type"\] \.guided-stepper\s*\{[\s\S]*display:\s*none/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.decision-help\s*\{[\s\S]*margin-top:\s*0/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.decision-help-grid\s*\{[\s\S]*gap:\s*8px/,
  );
});

test("mobile park calendar uses compact weekday labels", () => {
  const launcherJs = readFileSync(new URL("./launcher.js", import.meta.url), "utf8");

  assert.match(launcherJs, /label:\s*"M"[\s\S]*title:\s*"Monday"/);
  assert.match(launcherJs, /label:\s*"T"[\s\S]*title:\s*"Tuesday"/);
  assert.match(launcherJs, /setAttribute\("aria-label", weekday\.title\)/);
});

test("mobile review view stays readable with five workflow tabs", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /\.review-checklist/);
  assert.match(launcherCss, /\.review-step-grid/);
  assert.match(launcherCss, /\.review-count-grid/);
  assert.match(
    launcherCss,
    /@media \(max-width: 1024px\)[\s\S]*\.review-step-grid[\s\S]*grid-template-columns:\s*1fr/,
  );
});

test("mobile health exercise planner stays compact on iPhone SE width", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /\.health-exercise-panel/);
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.health-exercise-panel\s*\{[\s\S]*min-height:\s*0/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.health-week-days\s*\{[\s\S]*grid-template-columns:\s*1fr/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.health-session-form-grid\s*\{[\s\S]*grid-template-columns:\s*1fr/,
  );
  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.health-session-actions\s*\{[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/,
  );
});
