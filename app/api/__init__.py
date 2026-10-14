from fastapi import APIRouter

from app.api import devices, exports, health, imports, ingest, impressions, sessions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(impressions.router, prefix="/impressions", tags=["impressions"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
