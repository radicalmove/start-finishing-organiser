# Start Finishing Organiser (SFO)

Neon-themed, single-user organiser inspired by *Start Finishing*. Built on FastAPI, Jinja, and SQLite for quick iteration.

Current version: 0.722

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000 to see the prototype UI.

Web-first dev shortcut:

```bash
scripts/dev_web.sh
```

## Desktop app (macOS)

SFO can run as a native macOS app (Tauri shell + bundled FastAPI backend).
Current focus is web-first development; desktop build steps are optional for now.

Build the backend binary (PyInstaller) and the `.app` bundle:

```bash
scripts/build_macos_app.sh
```

Quick rebuild + open (auto-bumps the version pill):

```bash
scripts/rebuild_and_open_app.sh
```

The resulting app bundle will be in `src-tauri/target/release/bundle/macos/`.

Notes:
- If you want Gmail credentials bundled into the desktop app, place them at
  `src-tauri/resources/gmail_credentials.json` before building (the build script
  will also copy from any `client_secret*.json` in the repo root if present).

Notes:
- The app stores data in `~/Library/Application Support/com.rcd58.sfo/` (database is `sfo.db`).
- Gmail credentials are copied to `~/Library/Application Support/com.rcd58.sfo/gmail_credentials.json` on first run if bundled.
- Gmail tokens will be stored in the same folder as `gmail_token.json`.

Development (run backend manually):

```bash
uvicorn main:app --reload
cargo tauri dev
```

## Calendar feed (Cozi)

To show Cozi events in the calendar, set `COZI_ICS_URL` (either as an env var or via a local `.env` file in the repo root).

```bash
cp .env.example .env
# edit .env and set COZI_ICS_URL=...
```

## Authentication (recommended for remote access)

If you're planning to access SFO from multiple locations, enable login with a strong password:

```
SFO_PASSWORD=choose-a-long-password
SFO_SESSION_SECRET=generate-a-long-random-secret
```

Optional settings:

```
SFO_USERNAME=your-username
SFO_API_TOKEN=token-for-api-requests
SFO_HTTPS_ONLY=true
SFO_SESSION_SAMESITE=lax
SFO_SESSION_MAX_AGE=1209600
```

## Gmail inbox capture (optional)

To pull Gmail messages into the SFO inbox automatically, enable Gmail sync and authorize once.

Setup:

1. Create a Google Cloud OAuth client (Desktop app) and download the JSON.
2. Save it as `~/.config/sfo/gmail_credentials.json` (or update the path below).
3. Authorize once to generate a token:

```bash
python3 scripts/gmail_auth.py
```

Environment settings:

```
SFO_GMAIL_ENABLED=1
SFO_GMAIL_CLIENT_SECRETS=~/.config/sfo/gmail_credentials.json
SFO_GMAIL_TOKEN_PATH=~/.config/sfo/gmail_token.json
SFO_GMAIL_POLL_SECONDS=300
SFO_GMAIL_MAX_PER_SYNC=50
SFO_GMAIL_BACKFILL_DAYS=0
SFO_GMAIL_WORK_DOMAIN=canterbury.ac.nz
```

Notes:
- Backfill is off by default (sync starts “from now”). Set `SFO_GMAIL_BACKFILL_DAYS` if you want recent history imported.
- Emails are marked read after import.

Build tip:
- `SFO_SKIP_PIP=1` skips `pip install` during backend builds if you know your env is already up to date.

## Charlie coach (local LLM optional)

SFO includes a Charlie coach widget in the bottom-right of every screen after login. It will
use a local Ollama model if available, and fall back to a coach-lite mode if not.

Ask Charlie for a quick walkthrough of daily and weekly use. Long term planning lives at `/long-range`.

To enable Ollama:

```
# install Ollama app for macOS (https://ollama.com)
ollama pull llama3.1:8b
```

Optional settings:

```
SFO_LLM_PROVIDER=auto  # auto | ollama | off
SFO_OLLAMA_URL=http://localhost:11434
SFO_OLLAMA_MODEL=llama3.1:8b
SFO_LLM_TIMEOUT=15
SFO_COACH_HISTORY_LIMIT=120
```

## Stack

- FastAPI + Jinja2
- SQLAlchemy + SQLite (`sfo.db`)
- Vanilla JS/CSS (Simulation Theory neon palette)

## Early feature map

- Projects (work/personal) with a soft 4+3 weekly cap.
- Tasks with Today/Week/Month/Later buckets, frogs, alignment, block types, and a task board view.
- Blocks to reserve Focus/Admin/Social/Recovery time.
- Weekly review + resurfacing, plus a step-by-step weekly wizard.
- Success Packs and Waiting On slots (models in place; waiting UI available).
- Profile + onboarding wizard to anchor Why and weekly focus.
- Health dashboard at `/health`; health check at `/healthz`; JSON APIs under `/api`.
- Export center with JSON/CSV ZIP snapshots.

## Next steps

- Expand monthly/quarterly planning flows and review templates.
- Add richer analytics for health, tasks, and project momentum.
- Tighten coach intelligence and add more screen-aware guidance.
- Expand docs (architecture/setup) and add basic tests.
