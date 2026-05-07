from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    redis_url: str = "redis://localhost:6379/3"
    environment: str = "development"
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # Models directory — ONNX files loaded from here
    models_dir: str = "models"

    # Minimum acceptable test-set accuracy for a model to serve predictions.
    # Any stock whose best ensemble falls below this threshold gets predictions_disabled = True.
    model_accuracy_threshold: float = 0.53


settings = Settings()
