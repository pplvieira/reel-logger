from __future__ import annotations

from typing import Any

from app.services.platforms.base import PlatformAdapter, register

ALLOWED_INTERACTIONS = {
    "like",
    "unlike",
    "comment_open",
    "comment_send",
    "share_open",
    "send",
    "save",
    "profile_open",
}


class InstagramAdapter(PlatformAdapter):
    """Maps Instagram social-app meaning. No package names or view ids."""

    code = "instagram"

    def normalize_surface(self, payload: dict[str, Any]) -> str:
        surface = payload.get("surface") or "for_you"
        if not isinstance(surface, str):
            return "for_you"
        return surface

    def normalize_interaction_kind(self, payload: dict[str, Any]) -> str | None:
        kind = payload.get("kind")
        if isinstance(kind, str) and kind in ALLOWED_INTERACTIONS:
            return kind
        return None


register(InstagramAdapter())
