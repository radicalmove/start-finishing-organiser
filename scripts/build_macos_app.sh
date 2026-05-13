#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RESOURCE_DIR="$ROOT_DIR/src-tauri/resources"
RESOURCE_FILE="$RESOURCE_DIR/gmail_credentials.json"
mkdir -p "$RESOURCE_DIR"
if compgen -G "$ROOT_DIR/client_secret*.json" > /dev/null; then
  CREDENTIALS_FILE="$(ls -t "$ROOT_DIR"/client_secret*.json | head -1)"
  cp "$CREDENTIALS_FILE" "$RESOURCE_FILE"
  echo "Bundling Gmail credentials from $(basename "$CREDENTIALS_FILE")"
else
  if [[ ! -f "$RESOURCE_FILE" ]]; then
    : > "$RESOURCE_FILE"
  fi
  echo "No Gmail credentials found; bundling skipped."
fi

SFO_RUST_BACKEND_PROFILE=release scripts/build_rust_backend.sh

source "$HOME/.cargo/env"
cargo tauri build

APP_BUNDLE="$ROOT_DIR/src-tauri/target/release/bundle/macos/Start Finishing Organiser.app"
APP_BACKEND="$APP_BUNDLE/Contents/Resources/bin/sfo-server"
if [[ -d "$APP_BUNDLE" ]]; then
  mkdir -p "$(dirname "$APP_BACKEND")"
  cp "$ROOT_DIR/src-tauri/bin/sfo-server" "$APP_BACKEND"
  chmod +x "$APP_BACKEND"
fi

echo "Build complete. Check src-tauri/target/release/bundle/macos/ for the .app"
