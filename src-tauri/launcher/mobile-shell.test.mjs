import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const indexHtmlPath = new URL("./index.html", import.meta.url);
const launcherCssPath = new URL("./launcher.css", import.meta.url);

test("mobile shell opts into iOS safe-area layout", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(indexHtml, /viewport-fit=cover/);
  assert.match(launcherCss, /env\(safe-area-inset-top/);
  assert.match(launcherCss, /body::after/);
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
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.workflow-panel\s*\{[\s\S]*padding:\s*12px/);
  assert.match(launcherCss, /@media \(max-width: 430px\)[\s\S]*\.mini-button\s*\{[\s\S]*flex:\s*1 1 calc\(50% - 4px\)/);
});

test("mobile shell prevents iOS input focus zoom", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /input,\s*select,\s*textarea\s*\{[^}]*font-size:\s*16px/);
});

test("mobile process view puts the actionable queue before inbox stats", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.inbox-processing-panel\s*\{[\s\S]*order:\s*-1/);
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

test("mobile process controls stay inside iPhone SE width", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(
    launcherCss,
    /@media \(max-width: 430px\)[\s\S]*\.process-active-actions\s*\{[\s\S]*grid-template-columns:\s*1fr/,
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
