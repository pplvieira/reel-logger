from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_api_token
from app.core.db import get_db
from app.schemas.reporting import ImpressionOut
from app.services.reconcile import ReconcileResult, reconcile_impressions
from app.services.reporting import list_impressions

router = APIRouter(dependencies=[Depends(require_api_token)])


@router.get("", response_model=list[ImpressionOut])
def get_impressions(
    user_id: str = Query(...),
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[ImpressionOut]:
    return list_impressions(db, user_id=user_id, session_id=session_id)


@router.post("/reconcile", response_model=ReconcileResult)
def post_reconcile(
    user_id: str = Query(...),
    platform: str = Query("instagram"),
    db: Session = Depends(get_db),
) -> ReconcileResult:
    return reconcile_impressions(db, user_id=user_id, platform=platform)
