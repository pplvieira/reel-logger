import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.db import Base, get_db, init_engine
from app.main import create_app
from app.services.ingest import ensure_seed_user
import app.models  # noqa: F401


@pytest.fixture()
def client(monkeypatch):
    # Force a private in-memory DB for every test (never touch ./data/reel_logger.db).
    url = "sqlite://"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    engine = init_engine(url)
    # Recreate engine with StaticPool so all connections share one memory DB.
    from app.core import db as dbmod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    dbmod.engine = eng
    dbmod.SessionLocal = sessionmaker(bind=eng, autocommit=False, autoflush=False)
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)

    db = dbmod.SessionLocal()
    user = ensure_seed_user(db)
    db.close()

    application = create_app()

    def _override():
        session = dbmod.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _override
    # Lifespan would create_all on whatever get_engine() returns — keep it on eng.
    with TestClient(application) as test_client:
        test_client.seed_user_id = user.id  # type: ignore[attr-defined]
        yield test_client
    application.dependency_overrides.clear()
    get_settings.cache_clear()
