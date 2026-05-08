import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const indexHtmlPath = new URL("./index.html", import.meta.url);
const launcherJsPath = new URL("./launcher.js", import.meta.url);

test("launcher exposes the four top-level workflows", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  for (const workflow of ["today", "capture", "process", "settings"]) {
    assert.match(indexHtml, new RegExp(`data-workflow-tab="${workflow}"`));
    assert.match(indexHtml, new RegExp(`data-workflow-panel="${workflow}"`));
  }

  assert.match(indexHtml, /<nav class="workflow-nav"/);
  assert.match(indexHtml, /Today/);
  assert.match(indexHtml, /Capture/);
  assert.match(indexHtml, /Process/);
  assert.match(indexHtml, /Settings/);
});

test("connection settings are scoped to the Settings workflow", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");
  const settingsPanelStart = indexHtml.indexOf('data-workflow-panel="settings"');
  const connectionCard = indexHtml.indexOf('id="connection-card"');

  assert.ok(settingsPanelStart >= 0, "settings workflow exists");
  assert.ok(connectionCard > settingsPanelStart, "connection card lives inside settings");
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
  assert.match(launcherJs, /processPosition/);
  assert.match(launcherJs, /setWorkflow\("settings"\)/);
});
