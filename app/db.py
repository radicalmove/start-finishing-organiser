# Database configuration for Start Finishing Organiser
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./sfo.db"
SQLALCHEMY_DATABASE_URL = os.getenv("SFO_DATABASE_URL", DEFAULT_DATABASE_URL)


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def init_engine(db_url: str | None = None):
    """Initialize the SQLAlchemy engine and sessionmaker (used by tests)."""
    global engine, SessionLocal
    url = db_url or os.getenv("SFO_DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_engine(url, connect_args=_connect_args(url))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


engine = init_engine(SQLALCHEMY_DATABASE_URL)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_task_owner_column():
    """Ensure tasks.owner_type exists for ownership (mine/shared/OPP) classification."""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(tasks);")).fetchall()}
        if "owner_type" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN owner_type VARCHAR(10) NOT NULL DEFAULT 'mine'"
                )
            )


def ensure_task_resurface_columns():
    """Ensure tasks.resurface_on and tasks.duration_minutes exist."""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(tasks);")).fetchall()}
        if "resurface_on" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN resurface_on DATE NULL"
                )
            )
        if "duration_minutes" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN duration_minutes INTEGER NULL"
                )
            )


def ensure_block_title_column():
    """Ensure blocks.title exists for appointment/task labels."""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(blocks);")).fetchall()}
        if "title" not in cols:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN title VARCHAR(200) NULL"))


def ensure_ritual_table():
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ritual_entries (
                    id INTEGER PRIMARY KEY,
                    ritual_type VARCHAR(20) NOT NULL,
                    entry_date DATE NOT NULL,
                    grounding_movement TEXT NULL,
                    supplements_done BOOLEAN NULL,
                    plan_review TEXT NULL,
                    reality_scan TEXT NULL,
                    focus_time_status VARCHAR(40) NULL,
                    morning_right_now TEXT NULL,
                    morning_email_plan TEXT NULL,
                    morning_focus_chunk TEXT NULL,
                    one_thing TEXT NULL,
                    frog TEXT NULL,
                    gratitude TEXT NULL,
                    anticipation TEXT NULL,
                    why_reflection TEXT NULL,
                    why_expanded TEXT NULL,
                    block_plan TEXT NULL,
                    admin_plan TEXT NULL,
                    emotional_intent TEXT NULL,
                    midday_alignment VARCHAR(40) NULL,
                    midday_surprises TEXT NULL,
                    midday_one_thing TEXT NULL,
                    midday_frog TEXT NULL,
                    aar_went_well TEXT NULL,
                    aar_hard TEXT NULL,
                    aar_next_step TEXT NULL,
                    wins TEXT NULL,
                    adjustments TEXT NULL,
                    evening_shutdown TEXT NULL,
                    evening_breadcrumbs TEXT NULL,
                    energy VARCHAR(50) NULL,
                    notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )


def ensure_ritual_columns():
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(ritual_entries);")).fetchall()}
        if not cols:
            return
        if "grounding_movement" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN grounding_movement TEXT NULL"))
        if "supplements_done" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN supplements_done BOOLEAN NULL"))
        if "plan_review" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN plan_review TEXT NULL"))
        if "reality_scan" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN reality_scan TEXT NULL"))
        if "focus_time_status" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN focus_time_status VARCHAR(40) NULL"))
        if "morning_right_now" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN morning_right_now TEXT NULL"))
        if "morning_email_plan" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN morning_email_plan TEXT NULL"))
        if "morning_focus_chunk" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN morning_focus_chunk TEXT NULL"))
        if "anticipation" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN anticipation TEXT NULL"))
        if "why_expanded" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN why_expanded TEXT NULL"))
        if "block_plan" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN block_plan TEXT NULL"))
        if "admin_plan" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN admin_plan TEXT NULL"))
        if "emotional_intent" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN emotional_intent TEXT NULL"))
        if "midday_alignment" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN midday_alignment VARCHAR(40) NULL"))
        if "midday_surprises" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN midday_surprises TEXT NULL"))
        if "midday_one_thing" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN midday_one_thing TEXT NULL"))
        if "midday_frog" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN midday_frog TEXT NULL"))
        if "aar_went_well" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN aar_went_well TEXT NULL"))
        if "aar_hard" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN aar_hard TEXT NULL"))
        if "aar_next_step" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN aar_next_step TEXT NULL"))
        if "evening_shutdown" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN evening_shutdown TEXT NULL"))
        if "evening_breadcrumbs" not in cols:
            conn.execute(text("ALTER TABLE ritual_entries ADD COLUMN evening_breadcrumbs TEXT NULL"))


def ensure_guidance_reminder_columns():
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(guidance_reminders);")).fetchall()}
        if not cols:
            return
        if "snoozed_until" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE guidance_reminders "
                    "ADD COLUMN snoozed_until DATETIME NULL"
                )
            )


def ensure_task_inbox_column():
    """Ensure tasks.in_inbox exists for inbox processing flow."""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(tasks);")).fetchall()}
        if "in_inbox" not in cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN in_inbox BOOLEAN NOT NULL DEFAULT 0"))


def ensure_task_archived_from_inbox_column():
    """Ensure tasks.archived_from_inbox exists for inbox recycle bin restores."""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(tasks);")).fetchall()}
        if "archived_from_inbox" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN archived_from_inbox BOOLEAN NOT NULL DEFAULT 0"
                )
            )


def ensure_project_color_column():
    """Ensure projects.color_scheme exists for optional color tagging."""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(projects);")).fetchall()}
        if "color_scheme" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN color_scheme VARCHAR(24) NULL"))


def ensure_core_indexes():
    """Create lightweight indexes for frequently used single-user query paths."""
    statements = (
        "CREATE INDEX IF NOT EXISTS idx_tasks_inbox_status_created_at "
        "ON tasks (in_inbox, status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_bucket_status_created_at "
        "ON tasks (when_bucket, status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_resurface_on ON tasks (resurface_on)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_for ON tasks (scheduled_for)",
        "CREATE INDEX IF NOT EXISTS idx_blocks_date_start_time ON blocks (date, start_time)",
        "CREATE INDEX IF NOT EXISTS idx_waiting_on_last_followup ON waiting_on (last_followup)",
        "CREATE INDEX IF NOT EXISTS idx_ritual_entries_type_date ON ritual_entries (ritual_type, entry_date)",
        "CREATE INDEX IF NOT EXISTS idx_coach_messages_convo_created "
        "ON coach_messages (conversation_id, created_at)",
    )
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "init_engine",
    "ensure_task_owner_column",
    "ensure_task_resurface_columns",
    "ensure_block_title_column",
    "ensure_ritual_table",
    "ensure_ritual_columns",
    "ensure_guidance_reminder_columns",
    "ensure_task_inbox_column",
    "ensure_task_archived_from_inbox_column",
    "ensure_project_color_column",
    "ensure_core_indexes",
]
