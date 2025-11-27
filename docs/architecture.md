# Architecture Notes (prototype)

- **App shell**: FastAPI with Jinja templates; app factory in `app/__init__.py`. Static files live under `app/static`, templates under `app/templates`.
- **Database**: SQLite (`sfo.db`) via SQLAlchemy (`app/db.py`). `Base.metadata.create_all()` runs at startup.
- **Models** (`app/models.py`):
  - `Project` (work/personal, weekly active flag, size, success level, dates).
  - `Task` (verb–noun, when-bucket, block type, frog, alignment, status).
  - `Block` (Focus/Admin/Social/Recovery time slots, linked to project/task).
  - `SuccessPack` (guides/peers/supporters/beneficiaries, per project).
  - `WaitingOn` (pending items with people + follow-ups).
- **APIs**: JSON endpoints in `app/routes/api.py` for Projects/Tasks with soft 4+3 weekly enforcement on project activation.
- **UI**: Server-rendered Jinja. `home.html` shows Weekly Focus, Today tasks, and Blocks. Neon palette in `app/static/css/main.css` (Simulation Theory inspired).
- **Config**: Minimal; extend with `.env` and settings module if needed. Logging not yet wired (carry patterns from citation-checker if desired).
- **Entrypoint**: `main.py` exposes `app` for uvicorn and a `/health` endpoint.

## Stretch targets

- Add forms or HTMX/vanilla JS to create/update projects/tasks/blocks from the UI.
- Morning/Evening ritual panels and Steady Coach prompts.
- Persist profile/Why and energy preferences (single-user).
- Add simple migrations/helpers for schema tweaks (see `cdp-poc` and `citation-checker` patterns).
- Tests for API endpoints and cap enforcement.
