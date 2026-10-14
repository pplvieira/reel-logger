from __future__ import annotations

from typing import Any

from app.services.platforms.base import PlatformAdapter, register


class YouTubeShortsAdapter(PlatformAdapter):
    code = "youtube_shorts"
    implemented = False

    def normalize_surface(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError("YouTube Shorts adapter is a seam only; not implemented yet")

    def normalize_interaction_kind(self, payload: dict[str, Any]) -> str | None:
        raise NotImplementedError("YouTube Shorts adapter is a seam only; not implemented yet")


register(YouTubeShortsAdapter())
