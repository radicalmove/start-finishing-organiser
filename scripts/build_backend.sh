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

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r requirements.txt pyinstaller

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
