#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT_DIR/venv/bin/python3" ]]; then
    PYTHON_BIN="$ROOT_DIR/venv/bin/python3"
  elif [[ -x "$ROOT_DIR/.venv/bin/python3" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 not found. Install Python 3 and try again." >&2
  exit 1
fi

REQ_FILE="$ROOT_DIR/requirements.txt"
REQ_HASH_FILE="$ROOT_DIR/build/requirements.hash"
REQ_HASH=""
if command -v shasum >/dev/null 2>&1; then
  REQ_HASH="$(shasum -a 256 "$REQ_FILE" | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  REQ_HASH="$(sha256sum "$REQ_FILE" | awk '{print $1}')"
fi
PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
STAMP="${REQ_HASH}:${PY_VERSION}"

if [[ "${SFO_SKIP_PIP:-}" == "1" ]]; then
  echo "Skipping pip install (SFO_SKIP_PIP=1)"
elif [[ -n "$REQ_HASH" && -f "$REQ_HASH_FILE" && "$(cat "$REQ_HASH_FILE")" == "$STAMP" ]]; then
  echo "Requirements unchanged; skipping pip install."
else
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r requirements.txt pyinstaller
  if [[ -n "$REQ_HASH" ]]; then
    mkdir -p "$(dirname "$REQ_HASH_FILE")"
    echo "$STAMP" > "$REQ_HASH_FILE"
  fi
fi

"$PYTHON_BIN" -m PyInstaller \
  --clean \
  --noconfirm \
  --onefile \
  --name sfo-backend \
  --add-data "app/static:app/static" \
  --add-data "app/templates:app/templates" \
  scripts/desktop_entry.py

mkdir -p src-tauri/bin
cp "dist/sfo-backend" "src-tauri/bin/sfo-backend"
chmod +x "src-tauri/bin/sfo-backend"

echo "Backend binary ready at src-tauri/bin/sfo-backend"
