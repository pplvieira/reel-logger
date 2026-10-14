from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import require_api_token
from app.core.db import get_db
from app.models import Device, User
from app.schemas.events import DeviceCreate, DeviceOut, UserOut
from app.services.ingest import ensure_seed_user

router = APIRouter(dependencies=[Depends(require_api_token)])


@router.get("/users/me", response_model=UserOut)
def get_or_create_local_user(db: Session = Depends(get_db)) -> User:
    return ensure_seed_user(db)


@router.post("", response_model=DeviceOut)
def create_device(body: DeviceCreate, db: Session = Depends(get_db)) -> Device:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown user_id: {body.user_id}")
    device = Device(
        user_id=body.user_id,
        platform_os=body.platform_os,
        label=body.label,
        logger_version=body.logger_version,
        created_at=datetime.now(timezone.utc),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> list[Device]:
    return db.query(Device).filter(Device.user_id == user_id).order_by(Device.created_at.asc()).all()
