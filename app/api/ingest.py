from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_api_token
from app.core.db import get_db
from app.schemas.events import EventBatch, IngestResult
from app.services.ingest import ingest_batch

router = APIRouter(dependencies=[Depends(require_api_token)])


@router.post("/events", response_model=IngestResult)
def post_events(batch: EventBatch, db: Session = Depends(get_db)) -> IngestResult:
    return ingest_batch(db, batch)
