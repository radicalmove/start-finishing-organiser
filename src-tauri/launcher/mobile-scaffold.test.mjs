import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import test from "node:test";

const projectYmlPath = new URL("../gen/apple/project.yml", import.meta.url);
const xcodeProjectPath = new URL("../gen/apple/sfo.xcodeproj/project.pbxproj", import.meta.url);
const generatedAppIconPath = new URL("../gen/apple/Assets.xcassets/AppIcon.appiconset/", import.meta.url);
const canonicalIosIconPath = new URL("../icons/ios/", import.meta.url);
const iosBuildScriptPath = new URL("../../scripts/build_tauri_ios_simulator.sh", import.meta.url);
const cargoTomlPath = new URL("../Cargo.toml", import.meta.url);
const tauriConfigPath = new URL("../tauri.conf.json", import.meta.url);
const libRsPath = new URL("../src/lib.rs", import.meta.url);

test("iOS Xcode prebuild script prefers rustup cargo over Homebrew cargo", () => {
  const projectYml = readFileSync(projectYmlPath, "utf8");
  const xcodeProject = readFileSync(xcodeProjectPath, "utf8").replaceAll('\\"', '"');
  const expectedPrefix =
    'export PATH="$HOME/.cargo/bin:$PATH"; export CARGO="$HOME/.cargo/bin/cargo"; export RUSTC="$HOME/.cargo/bin/rustc"; "$CARGO" tauri ios xcode-script';

  assert.ok(projectYml.includes(expectedPrefix));
  assert.ok(xcodeProject.includes(expectedPrefix));
});

test("iOS simulator build wrapper clears stale generated bundle outputs", () => {
  const script = readFileSync(iosBuildScriptPath, "utf8");

  assert.match(
    script,
    /src-tauri\/gen\/apple\/build\/arm64-sim\/Start Finishing Organiser\.app/,
  );
  assert.match(
    script,
    /src-tauri\/gen\/apple\/build\/sfo_iOS\.xcarchive\/Products\/Applications\/Start Finishing Organiser\.app/,
  );
  assert.match(script, /rm -rf -- "\$SIM_APP_BUNDLE" "\$ARCHIVE_APP_BUNDLE"/);
  assert.match(script, /cargo tauri ios build --debug --target aarch64-sim --ci/);
});

test("iOS generated app icons match the canonical SFO icon set", () => {
  const contents = JSON.parse(readFileSync(new URL("Contents.json", generatedAppIconPath), "utf8"));
  const filenames = contents.images
    .map((image) => image.filename)
    .filter(Boolean);

  assert.ok(filenames.length > 0, "generated AppIcon catalog references PNG files");

  for (const filename of filenames) {
    const generatedHash = sha256(new URL(filename, generatedAppIconPath));
    const canonicalHash = sha256(new URL(filename, canonicalIosIconPath));

    assert.equal(generatedHash, canonicalHash, `${filename} should match canonical icon asset`);
  }
});

test("Tauri exposes API token commands to the static launcher", () => {
  const cargoToml = readFileSync(cargoTomlPath, "utf8");
  const tauriConfig = JSON.parse(readFileSync(tauriConfigPath, "utf8"));
  const libRs = readFileSync(libRsPath, "utf8");

  assert.match(cargoToml, /security-framework\s*=/);
  assert.equal(tauriConfig.app.withGlobalTauri, true);
  assert.match(libRs, /mod credential_store;/);
  assert.match(libRs, /#\[tauri::command\]\s*fn get_api_token/);
  assert.match(libRs, /#\[tauri::command\]\s*fn set_api_token/);
  assert.match(libRs, /#\[tauri::command\]\s*fn clear_api_token/);
  assert.match(
    libRs,
    /invoke_handler\(tauri::generate_handler!\[\s*get_api_token,\s*set_api_token,\s*clear_api_token,\s*\]\)/,
  );
});

function sha256(fileUrl) {
  return createHash("sha256").update(readFileSync(fileUrl)).digest("hex");
}
