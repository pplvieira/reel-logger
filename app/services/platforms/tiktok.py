from __future__ import annotations

from typing import Any

from app.services.platforms.base import PlatformAdapter, register


class TikTokAdapter(PlatformAdapter):
    code = "tiktok"
    implemented = False

    def normalize_surface(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError("TikTok adapter is a seam only; not implemented yet")

    def normalize_interaction_kind(self, payload: dict[str, Any]) -> str | None:
        raise NotImplementedError("TikTok adapter is a seam only; not implemented yet")


register(TikTokAdapter())
