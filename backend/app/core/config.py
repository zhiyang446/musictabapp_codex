"""核心設定模組。"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系統設定載入器，統一管理環境變數。"""

    api_v1_prefix: str = "/v1"
    project_name: str = "MusicTab API"
    supabase_url: str | None = None
    supabase_api_key: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """建立單例設定，避免重複解析設定來源。"""

    return Settings()


# settings 物件提供全域使用的設定值
settings: Settings = get_settings()
