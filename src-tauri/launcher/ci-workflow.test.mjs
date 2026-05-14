import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const ciWorkflowPath = new URL("../../.github/workflows/ci.yml", import.meta.url);

test("GitHub CI mirrors the local verification contract", () => {
  assert.ok(existsSync(ciWorkflowPath), "CI workflow should exist");

  const workflow = readFileSync(ciWorkflowPath, "utf8");

  assert.match(workflow, /pull_request:/);
  assert.match(workflow, /push:/);
  assert.match(workflow, /branches:\n\s+- main/);
  assert.doesNotMatch(workflow, /codex\/\*\*/);
  assert.match(workflow, /runs-on:\s*macos-latest/);
  assert.doesNotMatch(workflow, /FORCE_JAVASCRIPT_ACTIONS_TO_NODE24/);
  assert.match(workflow, /actions\/checkout@v6/);
  assert.match(workflow, /actions\/setup-node@v6/);
  assert.ok(workflow.includes("cargo fmt --all --check"));
  assert.ok(workflow.includes("cargo test --workspace"));
  assert.ok(workflow.includes("node --test src-tauri/launcher/*.test.mjs"));
  assert.ok(workflow.includes("cargo check --manifest-path src-tauri/Cargo.toml"));
  assert.ok(workflow.includes("git diff --check"));
});
