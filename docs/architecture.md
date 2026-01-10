# Architecture Notes (prototype)

- **App shell**: FastAPI with Jinja templates; app factory in `app/__init__.py`. Static files live under `app/static`, templates under `app/templates`.
- **Database**: SQLite (`sfo.db`) via SQLAlchemy (`app/db.py`). `Base.metadata.create_all()` runs at startup.
- **Models** (`app/models.py`):
  - `Project` (work/personal, weekly active flag, size, success level, dates).
  - `Task` (verb–noun, when-bucket, block type, frog, alignment, status).
  - `Block` (Focus/Admin/Social/Recovery time slots, linked to project/task).
  - `SuccessPack` (guides/peers/supporters/beneficiaries, per project).
  - `WaitingOn` (pending items with people + follow-ups).
  - `CoachConversation` + `CoachMessage` (Charlie coach chat history).
- **APIs**: JSON endpoints in `app/routes/api.py` for Projects/Tasks with soft 4+3 weekly enforcement on project activation.
- **Coach**: `/coach/history` and `/coach/message` endpoints with coach-lite and optional Ollama-backed responses (`app/utils/coach.py`).
- **UI**: Server-rendered Jinja. `home.html` shows Weekly Focus, Today tasks, and Blocks. Neon palette in `app/static/css/main.css` (Simulation Theory inspired).
- **Calendar**: Home has a Today timeline; full-width week view at `/calendar/week`. External events can be pulled from a Cozi ICS feed.
- **Long Term**: `/long-range` surfaces horizon planning, roadmaps, and momentum rhythm prompts.
- **Config**: Environment-first; a simple `.env` loader runs at startup (repo root `.env`, see `.env.example`). Key settings: `COZI_ICS_URL`, plus optional auth/session vars (`SFO_PASSWORD`, `SFO_SESSION_SECRET`). Logging not yet wired.
- **Entrypoint**: `main.py` exposes `app` for uvicorn and a `/healthz` endpoint (dashboard lives at `/health`).

## Stretch targets

- Add forms or HTMX/vanilla JS to create/update projects/tasks/blocks from the UI.
- Morning/Evening ritual panels and Steady Coach prompts.
- Persist profile/Why and energy preferences (single-user).
- Add simple migrations/helpers for schema tweaks (see `cdp-poc` and `citation-checker` patterns).
- Tests for API endpoints and cap enforcement.
