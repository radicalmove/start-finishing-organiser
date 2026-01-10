import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .db import (
    engine,
    Base,
    ensure_task_owner_column,
    ensure_task_resurface_columns,
    ensure_block_title_column,
    ensure_ritual_table,
    ensure_ritual_columns,
    ensure_guidance_reminder_columns,
)
from .routes import homepage, api, capture, blocks, resurface, weekly, waiting, ritual, auth, coach, long_range, nudges, health
from .security import ensure_csrf_token, current_user, is_authenticated, ui_auth_enabled
from .utils.health import ensure_health_metrics


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def create_app() -> FastAPI:
    """
    Application factory for the Start Finishing Organiser.
    Keeps startup logic tidy and makes testing easier.
    """
    _load_dotenv()
    Base.metadata.create_all(bind=engine)
    ensure_task_owner_column()
    ensure_task_resurface_columns()
    ensure_block_title_column()
    ensure_ritual_table()
    ensure_ritual_columns()
    ensure_guidance_reminder_columns()
    ensure_health_metrics()

    app = FastAPI(title="Start Finishing Organiser", version="0.1")

    def _parse_bool(value: str | None) -> bool:
        return bool(value) and value.strip().lower() in ("1", "true", "yes", "on")

    def _session_secret() -> str:
        secret = os.getenv("SFO_SESSION_SECRET") or os.getenv("SECRET_KEY")
        if ui_auth_enabled() and not secret:
            raise RuntimeError("SFO_SESSION_SECRET must be set when SFO_PASSWORD is enabled.")
        return secret or "dev-secret"

    session_max_age = os.getenv("SFO_SESSION_MAX_AGE")
    max_age = int(session_max_age) if session_max_age and session_max_age.isdigit() else None
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_secret(),
        same_site=os.getenv("SFO_SESSION_SAMESITE", "lax"),
        https_only=_parse_bool(os.getenv("SFO_HTTPS_ONLY")),
        max_age=max_age,
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    templates = Jinja2Templates(directory="app/templates")
    app.state.templates = templates
    templates.env.globals["csrf_token"] = ensure_csrf_token
    templates.env.globals["auth_enabled"] = ui_auth_enabled
    templates.env.globals["is_authenticated"] = is_authenticated
    templates.env.globals["current_user"] = current_user

    app.include_router(auth.router)
    app.include_router(homepage.router)
    app.include_router(capture.router)
    app.include_router(blocks.router)
    app.include_router(resurface.router)
    app.include_router(weekly.router)
    app.include_router(waiting.router)
    app.include_router(ritual.router)
    app.include_router(coach.router)
    app.include_router(nudges.router)
    app.include_router(long_range.router)
    app.include_router(health.router)
    app.include_router(api.router, prefix="/api")

    return app
