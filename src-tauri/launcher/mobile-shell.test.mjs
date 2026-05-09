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
  assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.hero-card/);
  assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.workflow-nav/);
});

test("mobile process view puts the actionable queue before inbox stats", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.inbox-processing-panel\s*\{[\s\S]*order:\s*-1/);
});
