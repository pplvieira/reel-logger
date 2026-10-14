from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.reporting import DaySummary, SessionOut
from app.services.reporting import day_summaries, list_sessions

router = APIRouter()


@router.get("/sessions", response_model=list[SessionOut])
def export_sessions(
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> list[SessionOut]:
    """Same payload as GET /sessions; reserved for later file export formats."""
    return list_sessions(db, user_id=user_id)


@router.get("/days", response_model=list[DaySummary])
def export_days(
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> list[DaySummary]:
    return day_summaries(db, user_id=user_id)
