#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_APP_BUNDLE="$ROOT_DIR/src-tauri/gen/apple/build/arm64-sim/Start Finishing Organiser.app"
ARCHIVE_APP_BUNDLE="$ROOT_DIR/src-tauri/gen/apple/build/sfo_iOS.xcarchive/Products/Applications/Start Finishing Organiser.app"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

rm -rf -- "$SIM_APP_BUNDLE" "$ARCHIVE_APP_BUNDLE"

cd "$ROOT_DIR/src-tauri"

cargo tauri ios build --debug --target aarch64-sim --ci
