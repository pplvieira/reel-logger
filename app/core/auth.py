from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """If API_TOKEN is set, require Bearer token. If empty, allow (localhost mode)."""
    settings = get_settings()
    expected = (settings.api_token or "").strip()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
