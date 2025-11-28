from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import engine, Base, ensure_task_owner_column, ensure_task_resurface_columns, ensure_ritual_table
from .routes import homepage, api, capture, blocks, resurface, weekly, waiting, ritual


def create_app() -> FastAPI:
    """
    Application factory for the Start Finishing Organiser.
    Keeps startup logic tidy and makes testing easier.
    """
    Base.metadata.create_all(bind=engine)
    ensure_task_owner_column()
    ensure_task_resurface_columns()
    ensure_ritual_table()

    app = FastAPI(title="Start Finishing Organiser", version="0.1")
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    templates = Jinja2Templates(directory="app/templates")
    app.state.templates = templates

    app.include_router(homepage.router)
    app.include_router(capture.router)
    app.include_router(blocks.router)
    app.include_router(resurface.router)
    app.include_router(weekly.router)
    app.include_router(waiting.router)
    app.include_router(ritual.router)
    app.include_router(api.router, prefix="/api")

    return app
