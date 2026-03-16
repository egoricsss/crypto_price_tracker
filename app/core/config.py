from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class DataBaseSettings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "crypto_db"
    db_user: str = "postgres"
    db_password: str = "postgres"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class RedisSettings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class AppSettings(BaseSettings):
    app_name: str = "Crypto Price Settings"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    # Время жизни токена или другие общие таймауты
    request_timeout: int = 30

    model_config = SettingsConfigDict(env_prefix="APP_")


class DeribitSettings(BaseSettings):
    base_url_test: str = "https://test.deribit.com"
    base_url: str = "https://www.deribit.com"
    request_timeout: int = 10

    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="DERIBIT_")


class CelerySettings(BaseSettings):
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list[str] = ["json"]
    timezone: str = "UTC+3"
    enable_utc: bool = True

    fetch_price_interval: int = 60

    model_config = SettingsConfigDict(env_prefix="CELERY_", env_nested_delimiter="__")


class Settings(BaseSettings):
    db: DataBaseSettings = DataBaseSettings()
    redis: RedisSettings = RedisSettings()
    app: AppSettings = AppSettings()
    deribit: DeribitSettings = DeribitSettings()
    celery: CelerySettings = CelerySettings()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
