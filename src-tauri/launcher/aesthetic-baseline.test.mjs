import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const launcherCssPath = new URL("./launcher.css", import.meta.url);
const indexHtmlPath = new URL("./index.html", import.meta.url);

test("launcher uses the adaptive SFO neon aesthetic baseline", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  assert.match(launcherCss, /--sfo-bg:\s*#05030f;/);
  assert.match(launcherCss, /--sfo-panel:\s*#0a0e23;/);
  assert.match(launcherCss, /--sfo-pink:\s*#ff2bd1;/);
  assert.match(launcherCss, /--sfo-blue:\s*#1987ff;/);
  assert.match(launcherCss, /--sfo-cyan:\s*#2da0ff;/);
  assert.match(launcherCss, /--sfo-glow:/);
  assert.match(indexHtml, /Start Finishing Organiser/);
  assert.doesNotMatch(indexHtml, /SFO Rust client/);

  assert.doesNotMatch(launcherCss, /--paper:/);
  assert.doesNotMatch(launcherCss, /--moss:/);
  assert.doesNotMatch(launcherCss, /--clay:/);
  assert.doesNotMatch(launcherCss, /Iowan Old Style/);
});

test("app header is compact and leaves room for workflow content", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  assert.match(indexHtml, /<section class="app-header"/);
  assert.match(launcherCss, /\.app-header\s*\{[\s\S]*min-height:\s*0/);
  assert.match(launcherCss, /\.app-header\s*\{[\s\S]*padding:\s*16px 18px/);
  assert.doesNotMatch(indexHtml, /Calm command centre/);
});

test("typography is calmer and small text remains readable", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /\.workflow-tab\s*\{[\s\S]*font-size:\s*18px/);
  assert.match(launcherCss, /\.workflow-tab\s*\{[\s\S]*font-weight:\s*650/);
  assert.match(launcherCss, /h2\s*\{[\s\S]*font-weight:\s*650/);
  assert.match(launcherCss, /h3\s*\{[\s\S]*font-weight:\s*650/);
  assert.match(launcherCss, /\.status-detail\s*\{[\s\S]*font-size:\s*14px/);
  assert.match(launcherCss, /\.panel-note\s*\{[\s\S]*font-size:\s*15px/);
  assert.match(launcherCss, /\.review-panel-title span\s*\{[^}]*font-size:\s*20px/);
  assert.match(launcherCss, /label\s*\{[\s\S]*font-size:\s*13px/);
});

test("routine action buttons use restrained glass styling", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /\.primary-button\s*\{[\s\S]*background:\s*rgba\(10, 14, 35, 0\.78\)/);
  assert.match(launcherCss, /\.primary-button\s*\{[\s\S]*border:\s*1px solid rgba\(45, 160, 255, 0\.42\)/);
  assert.match(launcherCss, /\.mini-button\s*\{[\s\S]*background:\s*rgba\(10, 14, 35, 0\.72\)/);
  assert.doesNotMatch(
    launcherCss,
    /\.mini-button\s*\{[\s\S]*background:\s*linear-gradient/,
  );
});

test("launcher keeps corner radii restrained", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /--sfo-radius-lg:\s*18px;/);
  assert.match(launcherCss, /--sfo-radius-md:\s*14px;/);
  assert.match(launcherCss, /--sfo-radius-sm:\s*10px;/);
  assert.doesNotMatch(launcherCss, /\.primary-button,[\s\S]*?border-radius:\s*999px/);
  assert.doesNotMatch(launcherCss, /\.mini-button\s*\{[\s\S]*?border-radius:\s*999px/);
  assert.doesNotMatch(launcherCss, /\.ghost-button[\s\S]*?border-radius:\s*999px/);
  assert.doesNotMatch(launcherCss, /\.workflow-tab[\s\S]*?border-radius:\s*999px/);
});

test("workflow shell has styled navigation and one-panel mobile layout", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.match(launcherCss, /\.workflow-nav\s*\{/);
  assert.match(launcherCss, /\.workflow-tab\s*\{/);
  assert.match(launcherCss, /\.workflow-tab\.is-active\s*\{/);
  assert.match(launcherCss, /\.workflow-panel\s*\{/);
  assert.match(launcherCss, /\.workflow-lede\s*\{/);
  assert.match(launcherCss, /\.process-primary\s*\{/);
  assert.match(launcherCss, /\.process-queue\s*\{/);
  assert.match(launcherCss, /\.settings-panel\s*\{/);
  assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.workflow-nav/);
});

test("workflow panels avoid display-toggle animations in the Tauri webview", () => {
  const launcherCss = readFileSync(launcherCssPath, "utf8");

  assert.doesNotMatch(
    launcherCss,
    /\.workflow-panel\s*\{[^}]*animation:\s*rise-in[^}]*both;/,
  );
});
