from sqlalchemy import text

from app import db as db_module


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
