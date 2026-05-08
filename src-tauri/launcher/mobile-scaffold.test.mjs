import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const projectYmlPath = new URL("../gen/apple/project.yml", import.meta.url);
const xcodeProjectPath = new URL("../gen/apple/sfo.xcodeproj/project.pbxproj", import.meta.url);

test("iOS Xcode prebuild script prefers rustup cargo over Homebrew cargo", () => {
  const projectYml = readFileSync(projectYmlPath, "utf8");
  const xcodeProject = readFileSync(xcodeProjectPath, "utf8").replaceAll('\\"', '"');
  const expectedPrefix =
    'export PATH="$HOME/.cargo/bin:$PATH"; export CARGO="$HOME/.cargo/bin/cargo"; export RUSTC="$HOME/.cargo/bin/rustc"; "$CARGO" tauri ios xcode-script';

  assert.ok(projectYml.includes(expectedPrefix));
  assert.ok(xcodeProject.includes(expectedPrefix));
});
