from sqlalchemy import text

from app import db as db_module


EXPECTED_INDEXES = {
    "tasks": {
        "idx_tasks_inbox_status_created_at",
        "idx_tasks_bucket_status_created_at",
        "idx_tasks_resurface_on",
        "idx_tasks_scheduled_for",
    },
    "blocks": {"idx_blocks_date_start_time"},
    "waiting_on": {"idx_waiting_on_last_followup"},
    "ritual_entries": {"idx_ritual_entries_type_date"},
    "coach_messages": {"idx_coach_messages_convo_created"},
}


def _index_names(table_name: str) -> set[str]:
    with db_module.engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA index_list('{table_name}')")).fetchall()
    return {row[1] for row in rows}


def test_ensure_core_indexes_creates_hot_path_indexes():
    db_module.ensure_core_indexes()
    for table_name, expected in EXPECTED_INDEXES.items():
        indexes = _index_names(table_name)
        for name in expected:
            assert name in indexes
