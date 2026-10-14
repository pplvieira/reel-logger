from app.services.platforms import instagram as _instagram  # noqa: F401
from app.services.platforms import tiktok as _tiktok  # noqa: F401
from app.services.platforms import youtube_shorts as _youtube_shorts  # noqa: F401
from app.services.platforms.base import PlatformAdapter, get_adapter
from app.services.platforms.instagram import InstagramAdapter

__all__ = ["PlatformAdapter", "get_adapter", "InstagramAdapter"]
