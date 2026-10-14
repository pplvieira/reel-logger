from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.auth import require_api_token
from app.core.db import get_db
from app.models import ContentRecord, User
from app.services.importers.dyi import (
    parse_liked_or_saved_document,
    parse_videos_watched_document,
)

router = APIRouter(dependencies=[Depends(require_api_token)])


class DyiImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    platform: str = "instagram"
    source: str = "dyi"
    document: Any = Field(
        ...,
        description="Parsed videos_watched.json / liked_posts.json body",
    )


class DyiImportResult(BaseModel):
    inserted: int
    with_url: int
    without_url: int


def _insert_rows(db: Session, user_id: str, platform: str, source: str, rows) -> DyiImportResult:
    with_url = 0
    without_url = 0
    for row in rows:
        if row.external_url:
            with_url += 1
        else:
            without_url += 1
        raw = dict(row.raw_json)
        if row.caption is not None:
            raw = {**raw, "_parsed_caption": row.caption}
        if row.fbid is not None:
            raw = {**raw, "_parsed_fbid": row.fbid}
        db.add(
            ContentRecord(
                user_id=user_id,
                platform=platform,
                source=source,
                creator_handle=row.creator_handle,
                external_url=row.external_url,
                watched_at=row.watched_at,
                time_precision=row.time_precision,
                raw_json=raw,
            )
        )
    db.commit()
    return DyiImportResult(inserted=len(rows), with_url=with_url, without_url=without_url)


@router.post("/dyi/videos-watched", response_model=DyiImportResult)
def import_dyi_videos_watched(
    body: DyiImportRequest,
    db: Session = Depends(get_db),
) -> DyiImportResult:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown user_id: {body.user_id}")
    rows = parse_videos_watched_document(body.document)
    return _insert_rows(db, body.user_id, body.platform, body.source or "dyi", rows)


@router.post("/dyi/liked-posts", response_model=DyiImportResult)
def import_dyi_liked_posts(
    body: DyiImportRequest,
    db: Session = Depends(get_db),
) -> DyiImportResult:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown user_id: {body.user_id}")
    rows = parse_liked_or_saved_document(body.document)
    return _insert_rows(db, body.user_id, body.platform, "dyi_liked", rows)


@router.post("/dyi/saved-posts", response_model=DyiImportResult)
def import_dyi_saved_posts(
    body: DyiImportRequest,
    db: Session = Depends(get_db),
) -> DyiImportResult:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown user_id: {body.user_id}")
    rows = parse_liked_or_saved_document(body.document)
    return _insert_rows(db, body.user_id, body.platform, "dyi_saved", rows)


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
