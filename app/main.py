from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import api_router
from app.core.config import DATA_DIR, get_settings
from app.core.db import Base, SessionLocal, get_engine
from app.services.ingest import ensure_seed_user

# Ensure model metadata is registered before create_all.
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    get_settings()
    Base.metadata.create_all(bind=get_engine())
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        ensure_seed_user(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Personal scroll logger",
        version=__version__,
        description="Semantic ingest and sessionize for personal short-form habit data.",
        lifespan=lifespan,
    )
    application.include_router(api_router)

    @application.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "reel-logger",
            "version": __version__,
            "docs": "/docs",
            "bind_hint": f"{settings.host}:{settings.port}",
        }

    return application


app = create_app()
