import logging
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import settings

logger = logging.getLogger("misunderstood.database")

# SQLite requires check_same_thread=False for multi-threaded FastAPI workers
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _safe_migrate_columns(engine_instance) -> None:
    """Non-destructive column migration for existing database files."""
    try:
        inspector = inspect(engine_instance)
        table_names = inspector.get_table_names()

        if "sessions" in table_names:
            session_cols = {col["name"] for col in inspector.get_columns("sessions")}
            with engine_instance.begin() as conn:
                if "join_code" not in session_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN join_code VARCHAR(32)"))
                if "context" not in session_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN context TEXT"))
                if "min_participants" not in session_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN min_participants INTEGER DEFAULT 2"))

        if "participants" in table_names:
            part_cols = {col["name"] for col in inspector.get_columns("participants")}
            with engine_instance.begin() as conn:
                if "display_name" not in part_cols:
                    conn.execute(text("ALTER TABLE participants ADD COLUMN display_name VARCHAR(100)"))
                if "role" not in part_cols:
                    conn.execute(text("ALTER TABLE participants ADD COLUMN role VARCHAR(32) DEFAULT 'participant'"))
                if "token_hash" not in part_cols:
                    conn.execute(text("ALTER TABLE participants ADD COLUMN token_hash VARCHAR(64)"))
                if "joined_at" not in part_cols:
                    conn.execute(text("ALTER TABLE participants ADD COLUMN joined_at TIMESTAMP"))
    except Exception as exc:
        logger.warning(f"Schema column check skipped or non-applicable: {exc}")


def init_db() -> None:
    import backend.app.models
    Base.metadata.create_all(bind=engine)
    _safe_migrate_columns(engine)
