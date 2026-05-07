#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_CONFIG="$ROOT_DIR/src-tauri/tauri.dev.conf.json"
APP_BUNDLE="$ROOT_DIR/src-tauri/target/debug/bundle/macos/Start Finishing Organiser Dev.app"

cd "$ROOT_DIR"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

pkill -f "$APP_BUNDLE/Contents/MacOS/sfo" || true

cargo tauri build --debug --bundles app --config "$DEV_CONFIG"

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "Dev app bundle not found at $APP_BUNDLE" >&2
  exit 1
fi

open -n -F "$APP_BUNDLE"
