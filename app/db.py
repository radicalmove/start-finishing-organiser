# Database configuration for Start Finishing Organiser
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./sfo.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
                    one_thing TEXT NULL,
                    frog TEXT NULL,
                    gratitude TEXT NULL,
                    why_reflection TEXT NULL,
                    wins TEXT NULL,
                    adjustments TEXT NULL,
                    energy VARCHAR(50) NULL,
                    notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )


__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "ensure_task_owner_column",
    "ensure_task_resurface_columns",
    "ensure_block_title_column",
    "ensure_ritual_table",
]
