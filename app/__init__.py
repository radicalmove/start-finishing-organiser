from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import engine, Base
from .routes import homepage, api


def create_app() -> FastAPI:
    """
    Application factory for the Start Finishing Organiser.
    Keeps startup logic tidy and makes testing easier.
    """
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="Start Finishing Organiser", version="0.1")
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    templates = Jinja2Templates(directory="app/templates")
    app.state.templates = templates

    app.include_router(homepage.router)
    app.include_router(api.router, prefix="/api")

    return app
