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
  assert.match(launcherJs, /renderTodayTasks/);
  assert.match(launcherJs, /processPosition/);
  assert.match(launcherJs, /setWorkflow\("settings"\)/);
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
  assert.match(launcherJs, /async function connectAndLoad\(\) \{\n\s+clearActionFeedback\(\);/);
});

test("launcher renders guided process as progressive steps", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /guidedProcessStepPlan/);
  assert.match(launcherJs, /function guidedStepSection\(/);
  assert.match(launcherJs, /dataset\.guidedStep/);
  assert.match(launcherJs, /function setGuidedStep\(/);
  assert.match(launcherJs, /data-guided-action/);
});
