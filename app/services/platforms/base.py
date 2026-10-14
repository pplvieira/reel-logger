"""Social-app adapters. Map platform meaning, not OS package names."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PlatformAdapter(ABC):
    code: str
    implemented: bool = True

    @abstractmethod
    def normalize_surface(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def normalize_interaction_kind(self, payload: dict[str, Any]) -> str | None:
        raise NotImplementedError


_REGISTRY: dict[str, PlatformAdapter] = {}


def register(adapter: PlatformAdapter) -> None:
    _REGISTRY[adapter.code] = adapter


def get_adapter(platform: str) -> PlatformAdapter:
    adapter = _REGISTRY.get(platform)
    if adapter is None:
        raise NotImplementedError(f"Platform adapter not registered: {platform}")
    if not adapter.implemented:
        raise NotImplementedError(f"Platform adapter not implemented: {platform}")
    return adapter
