from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{(DATA_DIR / 'reel_logger.db').as_posix()}"
    default_timezone: str = "Europe/Copenhagen"
    session_gap_seconds: int = 60
    api_token: str = ""
    host: str = "127.0.0.1"
    port: int = 8000
    seed_user_display_name: str = "local"
    schema_version: str = "1"


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
