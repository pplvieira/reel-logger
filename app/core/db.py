from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def _configure_sqlite(eng: Engine, database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return

    @event.listens_for(eng, "connect")
    def _sqlite_fk(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_engine(database_url: str | None = None) -> Engine:
    """Create (or recreate) the process-wide engine and session factory."""
    global engine, SessionLocal
    settings = get_settings()
    url = database_url or settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    eng = create_engine(url, connect_args=connect_args)
    _configure_sqlite(eng, url)
    engine = eng
    SessionLocal = sessionmaker(bind=eng, autocommit=False, autoflush=False)
    return eng


def get_engine() -> Engine:
    if engine is None:
        return init_engine()
    return engine


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        init_engine()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Eager default for normal app use; tests may call init_engine() again.
init_engine()
