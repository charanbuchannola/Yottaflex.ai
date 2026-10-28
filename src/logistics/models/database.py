"""Database Engine, Session Management, and Pragmas."""

from collections.abc import Generator
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from logistics.config import settings
from logistics.models.base import Base


def create_db_engine(db_url: str | None = None) -> Engine:
    """Create a configured SQLAlchemy engine with SQLite pragmas enabled."""
    url = db_url or settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        connect_args=connect_args,
        echo=False,
    )

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()

    return engine


# Default singleton engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session for FastAPI dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine: Engine | None = None) -> None:
    """Ensure database directories exist and create all metadata tables."""
    settings.ensure_directories()
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


def drop_db(target_engine: Engine | None = None) -> None:
    """Drop all metadata tables."""
    eng = target_engine or engine
    Base.metadata.drop_all(bind=eng)
