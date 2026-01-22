import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test.db"
    os.environ["SFO_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SFO_API_TOKEN"] = "test-token"

    from app import db as db_module

    db_module.init_engine(os.environ["SFO_DATABASE_URL"])

    from app import create_app

    return create_app()


@pytest.fixture(autouse=True)
def reset_db():
    from app.db import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def api_headers():
    return {"x-api-key": os.environ["SFO_API_TOKEN"]}


@pytest.fixture
def db_session():
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
