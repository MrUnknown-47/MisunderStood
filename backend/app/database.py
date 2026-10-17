import json
import uuid
from typing import Generator, Any
from sqlalchemy import create_engine, TypeDecorator, CHAR, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified UUID hex.
    """
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(str(value))
            return value


class UniversalJSON(TypeDecorator):
    """Platform-independent JSON type.
    Uses PostgreSQL's JSONB type if available, otherwise fallback to generic JSON.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
