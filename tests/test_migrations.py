from sqlalchemy import text

from app import db as db_module
from app.models import Base, HealthMetric
from app.utils import health as health_utils


def _table_exists(name: str) -> bool:
    with db_module.engine.connect() as conn:
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": name},
        ).fetchone()
    return row is not None


def test_apply_schema_migrations_tracks_revisions_and_is_idempotent():
    with db_module.engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))

    assert _table_exists("schema_migrations") is False

    first_applied = db_module.apply_schema_migrations()
    assert len(first_applied) == len(db_module.SCHEMA_MIGRATIONS)
    assert _table_exists("schema_migrations") is True

    listed = db_module.list_schema_migrations()
    assert len(listed) == len(db_module.SCHEMA_MIGRATIONS)
    assert listed[-1]["revision"] == db_module.SCHEMA_MIGRATIONS[-1].revision

    second_applied = db_module.apply_schema_migrations()
    assert second_applied == []


def test_ensure_health_metrics_uses_current_engine(tmp_path):
    original_url = str(db_module.engine.url)
    new_db = tmp_path / "health_metrics.db"
    try:
        db_module.init_engine(f"sqlite:///{new_db}")
        Base.metadata.create_all(bind=db_module.engine)

        health_utils.ensure_health_metrics()

        session = db_module.SessionLocal()
        try:
            assert session.query(HealthMetric).count() == len(health_utils.DEFAULT_METRICS)
        finally:
            session.close()
    finally:
        db_module.init_engine(original_url)
