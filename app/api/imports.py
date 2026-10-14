from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import ContentRecord, User
from app.services.importers.dyi import parse_videos_watched_document

router = APIRouter()


class DyiImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    platform: str = "instagram"
    document: Any = Field(
        ...,
        description="Parsed videos_watched.json body (array or wrapped object)",
    )


class DyiImportResult(BaseModel):
    inserted: int
    with_url: int
    without_url: int


@router.post("/dyi/videos-watched", response_model=DyiImportResult)
def import_dyi_videos_watched(
    body: DyiImportRequest,
    db: Session = Depends(get_db),
) -> DyiImportResult:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown user_id: {body.user_id}")

    rows = parse_videos_watched_document(body.document)
    with_url = 0
    without_url = 0
    for row in rows:
        if row.external_url:
            with_url += 1
        else:
            without_url += 1
        db.add(
            ContentRecord(
                user_id=body.user_id,
                platform=body.platform,
                source="dyi",
                creator_handle=row.creator_handle,
                external_url=row.external_url,
                watched_at=row.watched_at,
                time_precision=row.time_precision,
                raw_json=row.raw_json,
            )
        )
    db.commit()
    return DyiImportResult(inserted=len(rows), with_url=with_url, without_url=without_url)


class ManualUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    platform: str = "instagram"
    external_url: str
    creator_handle: str | None = None
    watched_at: datetime | None = None
    capture_method: str = "manual"


@router.post("/manual-url", response_model=dict)
def import_manual_url(body: ManualUrlRequest, db: Session = Depends(get_db)) -> dict:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown user_id: {body.user_id}")
    record = ContentRecord(
        user_id=body.user_id,
        platform=body.platform,
        source=body.capture_method,
        creator_handle=body.creator_handle,
        external_url=body.external_url,
        watched_at=body.watched_at or datetime.now(timezone.utc),
        time_precision="second" if body.watched_at else "unknown",
        raw_json=body.model_dump(mode="json"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "external_url": record.external_url}
