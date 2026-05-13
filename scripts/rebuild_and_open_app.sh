#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_BUNDLE="$ROOT_DIR/src-tauri/target/release/bundle/macos/Start Finishing Organiser.app"
APP_BACKEND="$APP_BUNDLE/Contents/Resources/bin/sfo-server"

python3 "$ROOT_DIR/scripts/bump_version_pill.py"

pkill -f "Start Finishing Organiser.app/Contents/MacOS/sfo" || true
pkill -f "sfo-server" || true

SFO_RUST_BACKEND_PROFILE=release "$ROOT_DIR/scripts/build_rust_backend.sh"

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "App bundle not found at $APP_BUNDLE" >&2
  echo "Run scripts/build_macos_app.sh to create the .app bundle first." >&2
  exit 1
fi

mkdir -p "$(dirname "$APP_BACKEND")"
cp "$ROOT_DIR/src-tauri/bin/sfo-server" "$APP_BACKEND"
chmod +x "$APP_BACKEND"

open "$APP_BUNDLE"
