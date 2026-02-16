#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

venv_has_modules() {
  local env_dir="$1"
  shift
  "$env_dir/bin/python" - "$@" <<'PY'
import importlib.util as util
import sys

mods = sys.argv[1:]
missing = [mod for mod in mods if util.find_spec(mod) is None]
sys.exit(0 if not missing else 1)
PY
}

gmail_enabled=0
if [[ "${SFO_GMAIL_ENABLED:-}" =~ ^(1|true|yes|on)$ ]]; then
  gmail_enabled=1
elif [[ -f ".env" ]] && grep -Eiq '^\s*SFO_GMAIL_ENABLED\s*=\s*(1|true|yes|on)\s*$' ".env"; then
  gmail_enabled=1
fi

required_modules=(fastapi uvicorn)
if [[ "$gmail_enabled" -eq 1 ]]; then
  required_modules+=(google.auth google_auth_oauthlib googleapiclient.discovery)
fi

selected_env=""
for candidate in "venv" ".venv"; do
  if [[ ! -x "$candidate/bin/python" ]]; then
    continue
  fi
  if venv_has_modules "$candidate" "${required_modules[@]}"; then
    selected_env="$candidate"
    break
  fi
done

if [[ -z "$selected_env" ]]; then
  for candidate in "venv" ".venv"; do
    if [[ -f "$candidate/bin/activate" ]]; then
      selected_env="$candidate"
      break
    fi
  done
fi

if [[ -n "$selected_env" ]]; then
  # shellcheck disable=SC1091
  source "$selected_env/bin/activate"
  echo "Using virtualenv: $selected_env"
fi

# Keep web and desktop data in sync by default for local single-user runs.
# Explicit SFO_DATABASE_URL always wins.
if [[ -z "${SFO_DATABASE_URL:-}" ]]; then
  app_support_db="$HOME/Library/Application Support/com.rcd58.sfo/sfo.db"
  if [[ -f "$app_support_db" ]]; then
    export SFO_DATABASE_URL="sqlite:///$app_support_db"
    echo "Using database: $app_support_db"
  fi
fi

export SFO_TAURI=0
export WATCHFILES_FORCE_POLLING="${WATCHFILES_FORCE_POLLING:-1}"

if [[ "${SFO_DISABLE_RELOAD:-0}" == "1" ]]; then
  uvicorn main:app
  exit $?
fi

set +e
uvicorn main:app --reload
status=$?
set -e

if [[ $status -ne 0 ]]; then
  echo "Reload failed; falling back to non-reload server."
  uvicorn main:app
fi
