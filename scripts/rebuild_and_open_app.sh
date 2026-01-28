#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_BUNDLE="$ROOT_DIR/src-tauri/target/release/bundle/macos/Start Finishing Organiser.app"
APP_BACKEND="$APP_BUNDLE/Contents/Resources/bin/sfo-backend"

python3 "$ROOT_DIR/scripts/bump_version_pill.py"

pkill -f "Start Finishing Organiser.app/Contents/MacOS/sfo" || true
pkill -f "sfo-backend" || true

"$ROOT_DIR/scripts/build_backend.sh"

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "App bundle not found at $APP_BUNDLE" >&2
  echo "Run scripts/build_macos_app.sh to create the .app bundle first." >&2
  exit 1
fi

if [[ -f "$APP_BACKEND" ]]; then
  cp "$ROOT_DIR/src-tauri/bin/sfo-backend" "$APP_BACKEND"
fi

open "$APP_BUNDLE"
