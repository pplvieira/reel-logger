from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.reporting import DaySummary, SessionOut
from app.services.reporting import day_summaries, list_sessions

router = APIRouter()


@router.get("", response_model=list[SessionOut])
def get_sessions(
    user_id: str = Query(...),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[SessionOut]:
    return list_sessions(db, user_id=user_id, platform=platform)


@router.get("/days", response_model=list[DaySummary])
def get_day_summaries(
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> list[DaySummary]:
    return day_summaries(db, user_id=user_id)
