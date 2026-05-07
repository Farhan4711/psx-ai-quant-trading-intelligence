from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://psx_user:psx_pass@localhost:5432/psx_dev"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    environment: str = "development"
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # Object storage for raw response archiving
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_bucket_name: str = "psx-raw-data"

    # Rate limiting — min seconds between requests to same domain
    # PSX DATA LICENSING NOTICE: see LICENSING_NOTICE.md
    scraper_min_delay_seconds: float = 3.0


settings = Settings()
