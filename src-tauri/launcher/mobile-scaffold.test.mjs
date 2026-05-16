import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { inflateSync } from "node:zlib";
import test from "node:test";

const projectYmlPath = new URL("../gen/apple/project.yml", import.meta.url);
const xcodeProjectPath = new URL("../gen/apple/sfo.xcodeproj/project.pbxproj", import.meta.url);
const generatedAppIconPath = new URL("../gen/apple/Assets.xcassets/AppIcon.appiconset/", import.meta.url);
const canonicalIosIconPath = new URL("../icons/ios/", import.meta.url);
const iosBuildScriptPath = new URL("../../scripts/build_tauri_ios_simulator.sh", import.meta.url);
const cargoTomlPath = new URL("../Cargo.toml", import.meta.url);
const tauriConfigPath = new URL("../tauri.conf.json", import.meta.url);
const tauriCapabilitiesPath = new URL("../capabilities/default.json", import.meta.url);
const libRsPath = new URL("../src/lib.rs", import.meta.url);
const iosInfoPlistPath = new URL("../gen/apple/sfo_iOS/Info.plist", import.meta.url);

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

test("iOS Xcode project packages standalone iPhone app icon files", () => {
  const xcodeProject = readFileSync(xcodeProjectPath, "utf8").replaceAll('\\"', '"');
  const projectYml = readFileSync(projectYmlPath, "utf8");
  const infoPlist = readFileSync(iosInfoPlistPath, "utf8");
  const resourcesPhase = xcodeProject.match(
    /\/\* Begin PBXResourcesBuildPhase section \*\/[\s\S]*?\/\* End PBXResourcesBuildPhase section \*\//,
  )?.[0];

  assert.doesNotMatch(projectYml, /^\s+- path: Assets\.xcassets$/m);
  assert.match(projectYml, /AppIcon-60x60@2x\.png/);
  assert.match(projectYml, /AppIcon-60x60@3x\.png/);
  assert.doesNotMatch(resourcesPhase, /Assets\.xcassets in Resources/);
  assert.match(resourcesPhase, /AppIcon-60x60@2x\.png in Resources/);
  assert.match(resourcesPhase, /AppIcon-60x60@3x\.png in Resources/);
  assert.doesNotMatch(resourcesPhase, /LaunchScreen\.storyboard in Resources/);
  assert.match(infoPlist, /<key>CFBundleIcons<\/key>/);
  assert.match(infoPlist, /<string>AppIcon-60x60@2x\.png<\/string>/);
  assert.match(infoPlist, /<string>AppIcon-60x60@3x\.png<\/string>/);
});

test("iOS app icon uses full-bleed artwork without a white matte", () => {
  const highResolutionIcon = decodeRgbaPng(new URL("AppIcon-512@2x.png", canonicalIosIconPath));
  const corners = [
    highResolutionIcon.pixel(0, 0),
    highResolutionIcon.pixel(highResolutionIcon.width - 1, 0),
    highResolutionIcon.pixel(0, highResolutionIcon.height - 1),
    highResolutionIcon.pixel(highResolutionIcon.width - 1, highResolutionIcon.height - 1),
  ];

  for (const [red, green, blue, alpha] of corners) {
    assert.equal(alpha, 255, "iOS app icons should be fully opaque");
    assert.notDeepEqual([red, green, blue], [255, 255, 255], "corner pixels should not be white");
  }
});

test("iOS package declares a storyboard-free launch screen for full-size phone layout", () => {
  const projectYml = readFileSync(projectYmlPath, "utf8");
  const infoPlist = readFileSync(iosInfoPlistPath, "utf8");

  assert.match(projectYml, /UILaunchScreen:\s*\{\}/);
  assert.doesNotMatch(projectYml, /UILaunchStoryboardName/);
  assert.match(infoPlist, /<key>UILaunchScreen<\/key>\s*<dict\/>/);
  assert.doesNotMatch(infoPlist, /UILaunchStoryboardName/);
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

test("Tauri notification plugin is available for native SFO reminders", () => {
  const cargoToml = readFileSync(cargoTomlPath, "utf8");
  const capabilities = JSON.parse(readFileSync(tauriCapabilitiesPath, "utf8"));
  const libRs = readFileSync(libRsPath, "utf8");

  assert.match(cargoToml, /tauri-plugin-notification\s*=/);
  assert.ok(capabilities.permissions.includes("notification:default"));
  assert.match(libRs, /\.plugin\(tauri_plugin_notification::init\(\)\)/);
});

function sha256(fileUrl) {
  return createHash("sha256").update(readFileSync(fileUrl)).digest("hex");
}

function decodeRgbaPng(fileUrl) {
  const file = readFileSync(fileUrl);
  assert.equal(file.toString("ascii", 1, 4), "PNG");

  let offset = 8;
  let width = 0;
  let height = 0;
  let colorType = 0;
  const idatChunks = [];
  while (offset < file.length) {
    const length = file.readUInt32BE(offset);
    const type = file.toString("ascii", offset + 4, offset + 8);
    const data = file.subarray(offset + 8, offset + 8 + length);
    if (type === "IHDR") {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      assert.equal(data[8], 8, "test PNG decoder expects 8-bit images");
      colorType = data[9];
      assert.equal(data[12], 0, "test PNG decoder expects non-interlaced images");
    } else if (type === "IDAT") {
      idatChunks.push(data);
    } else if (type === "IEND") {
      break;
    }
    offset += 12 + length;
  }

  assert.equal(colorType, 6, "test PNG decoder expects RGBA images");
  const channels = 4;
  const stride = width * channels;
  const inflated = inflateSync(Buffer.concat(idatChunks));
  const pixels = Buffer.alloc(width * height * channels);
  let inputOffset = 0;
  let outputOffset = 0;
  let previous = Buffer.alloc(stride);

  for (let row = 0; row < height; row += 1) {
    const filter = inflated[inputOffset];
    inputOffset += 1;
    const current = Buffer.from(inflated.subarray(inputOffset, inputOffset + stride));
    inputOffset += stride;
    unfilterScanline(current, previous, filter, channels);
    current.copy(pixels, outputOffset);
    outputOffset += stride;
    previous = current;
  }

  return {
    width,
    height,
    pixel(x, y) {
      const pixelOffset = (y * width + x) * channels;
      return [
        pixels[pixelOffset],
        pixels[pixelOffset + 1],
        pixels[pixelOffset + 2],
        pixels[pixelOffset + 3],
      ];
    },
  };
}

function unfilterScanline(current, previous, filter, channels) {
  for (let index = 0; index < current.length; index += 1) {
    const left = index >= channels ? current[index - channels] : 0;
    const up = previous[index] || 0;
    const upLeft = index >= channels ? previous[index - channels] || 0 : 0;
    if (filter === 1) {
      current[index] = (current[index] + left) & 255;
    } else if (filter === 2) {
      current[index] = (current[index] + up) & 255;
    } else if (filter === 3) {
      current[index] = (current[index] + Math.floor((left + up) / 2)) & 255;
    } else if (filter === 4) {
      current[index] = (current[index] + paethPredictor(left, up, upLeft)) & 255;
    } else {
      assert.equal(filter, 0, `unsupported PNG filter ${filter}`);
    }
  }
}

function paethPredictor(left, up, upLeft) {
  const estimate = left + up - upLeft;
  const leftDistance = Math.abs(estimate - left);
  const upDistance = Math.abs(estimate - up);
  const upLeftDistance = Math.abs(estimate - upLeft);
  if (leftDistance <= upDistance && leftDistance <= upLeftDistance) return left;
  if (upDistance <= upLeftDistance) return up;
  return upLeft;
}
