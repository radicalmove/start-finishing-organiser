import os
import time
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .db import (
    Base,
    apply_schema_migrations,
)
from .routes import homepage, api, capture, blocks, resurface, weekly, waiting, ritual, auth, coach, long_range, nudges, health, profile, onboarding, tasks, export
from .security import ensure_csrf_token, current_user, is_authenticated, ui_auth_enabled
from .utils.health import ensure_health_metrics
from .utils.gmail import start_gmail_sync_loop

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    candidates: list[Path] = []
    override = os.getenv("SFO_ENV_PATH")
    if override:
        candidates.append(Path(override).expanduser())
    candidates.append(Path(__file__).resolve().parent.parent / ".env")
    candidates.append(Path.home() / ".config" / "sfo" / ".env")

    for env_path in candidates:
        if not env_path.exists():
            continue
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
    from . import models  # noqa: F401
    from . import db as db_module

    Base.metadata.create_all(bind=db_module.engine)
    apply_schema_migrations()
    ensure_health_metrics()

    app = FastAPI(title="Start Finishing Organiser", version="0.7.0")
    app.state.startup_error = None
    app.state.startup_warnings = []

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

    if os.getenv("SFO_TAURI") == "1":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "tauri://localhost",
                "https://tauri.localhost",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app_dir = Path(__file__).resolve().parent
    app.mount("/static", StaticFiles(directory=str(app_dir / "static")), name="static")

    templates = Jinja2Templates(directory=str(app_dir / "templates"))
    app.state.templates = templates
    templates.env.globals["csrf_token"] = ensure_csrf_token
    templates.env.globals["auth_enabled"] = ui_auth_enabled
    templates.env.globals["is_authenticated"] = is_authenticated
    templates.env.globals["current_user"] = current_user
    templates.env.globals["static_version"] = os.getenv("SFO_STATIC_VERSION") or str(
        int(time.time())
    )

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
    app.include_router(profile.router)
    app.include_router(onboarding.router)
    app.include_router(tasks.router)
    app.include_router(export.router)
    app.include_router(api.router, prefix="/api")

    try:
        start_gmail_sync_loop()
    except Exception as exc:
        warning = f"Gmail sync did not start: {type(exc).__name__}: {exc}"
        app.state.startup_warnings.append(warning)
        logger.exception("Gmail sync startup failed")

    return app
