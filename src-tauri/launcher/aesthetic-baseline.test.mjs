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
  assert.match(indexHtml, /SFO Rust client/);

  assert.doesNotMatch(launcherCss, /--paper:/);
  assert.doesNotMatch(launcherCss, /--moss:/);
  assert.doesNotMatch(launcherCss, /--clay:/);
  assert.doesNotMatch(launcherCss, /Iowan Old Style/);
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
