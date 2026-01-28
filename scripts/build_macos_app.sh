#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

scripts/build_backend.sh

source "$HOME/.cargo/env"
cargo tauri build

echo "Build complete. Check src-tauri/target/release/bundle/macos/ for the .app"
