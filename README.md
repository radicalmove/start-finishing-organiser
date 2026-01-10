# Start Finishing Organiser (SFO)

Neon-themed, single-user organiser inspired by *Start Finishing*. Built on FastAPI, Jinja, and SQLite for quick iteration.

Current version: 0.5

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000 to see the prototype UI.

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
