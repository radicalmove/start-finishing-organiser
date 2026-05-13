#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${SFO_RUST_BACKEND_PROFILE:-debug}"
TARGET_TRIPLE="${SFO_RUST_BACKEND_TARGET:-$(rustc -vV | awk '/^host:/ { print $2 }')}"

cd "$ROOT_DIR"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

if [[ "$PROFILE" == "release" ]]; then
  cargo build -p sfo-server --release
  SOURCE_BIN="$ROOT_DIR/target/release/sfo-server"
else
  cargo build -p sfo-server
  SOURCE_BIN="$ROOT_DIR/target/debug/sfo-server"
fi

mkdir -p "$ROOT_DIR/src-tauri/bin"
cp "$SOURCE_BIN" "$ROOT_DIR/src-tauri/bin/sfo-server"
cp "$SOURCE_BIN" "$ROOT_DIR/src-tauri/bin/sfo-server-$TARGET_TRIPLE"
chmod +x "$ROOT_DIR/src-tauri/bin/sfo-server" "$ROOT_DIR/src-tauri/bin/sfo-server-$TARGET_TRIPLE"

echo "Rust backend ready at src-tauri/bin/sfo-server"
