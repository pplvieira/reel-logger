import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import Base, SessionLocal, get_db, get_engine, init_engine
from app.main import create_app
from app.services.ingest import ensure_seed_user
import app.models  # noqa: F401


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    init_engine(url)
    Base.metadata.create_all(bind=get_engine())

    assert SessionLocal is not None
    db = SessionLocal()
    user = ensure_seed_user(db)
    db.close()

    application = create_app()

    def _override():
        assert SessionLocal is not None
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _override
    with TestClient(application) as test_client:
        test_client.seed_user_id = user.id  # type: ignore[attr-defined]
        yield test_client
    application.dependency_overrides.clear()
    get_settings.cache_clear()
