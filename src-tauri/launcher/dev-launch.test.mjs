import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const devConfigPath = new URL("../tauri.dev.conf.json", import.meta.url);
const launchScriptPath = new URL("../../scripts/run_tauri_dev_shell.sh", import.meta.url);

test("dev Tauri config uses a distinct macOS identity", () => {
  const config = JSON.parse(readFileSync(devConfigPath, "utf8"));

  assert.equal(config.identifier, "com.rcd58.sfo.dev");
  assert.equal(config.productName, "Start Finishing Organiser Dev");
  assert.equal(config.app.windows[0].title, "Start Finishing Organiser Dev");
  assert.notEqual(config.identifier, "com.rcd58.sfo");
  assert.notEqual(config.productName, "Start Finishing Organiser");
});

test("dev shell launch script builds and opens the dev app bundle", () => {
  const script = readFileSync(launchScriptPath, "utf8");

  assert.match(script, /tauri\.dev\.conf\.json/);
  assert.match(script, /cargo tauri build --debug --bundles app --config/);
  assert.match(script, /Start Finishing Organiser Dev\.app/);
  assert.doesNotMatch(script, /Start Finishing Organiser\.app\/Contents\/MacOS\/sfo/);
});
