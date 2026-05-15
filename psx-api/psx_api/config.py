from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://psx_user:psx_pass@localhost:5432/psx_dev"
    database_test_url: str = "postgresql+asyncpg://psx_user:psx_pass@localhost:5432/psx_test"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Auth
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # App
    environment: str = "development"
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:3000"

    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@psxai.com"
    smtp_use_tls: bool = True
    # Frontend URL for building email links
    frontend_url: str = "http://localhost:3000"

    # Sentry
    sentry_dsn: str = ""

    # Inference service
    inference_service_url: str = "http://localhost:8001"

    # Object storage
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_bucket_name: str = "psx-raw-data"

    # ── Payment gateways (Pakistan) ───────────────────────────────────
    # Empty creds → the gateway runs in sandbox mode and returns a
    # mock checkout URL pointing at our /billing/sandbox-return page,
    # so the full flow can be exercised without merchant onboarding.
    # Set these in production to switch each gateway live.
    payments_base_url: str = "http://localhost:8000"  # used for callback URLs
    payments_return_url: str = "http://localhost:3000/checkout/return"

    # JazzCash (HBL Pay) — HTTP POST + HMAC-SHA256
    # https://sandbox.jazzcash.com.pk/  (Sandbox)
    # https://payments.jazzcash.com.pk/ (Live)
    jazzcash_merchant_id: str = ""
    jazzcash_password: str = ""
    jazzcash_integrity_salt: str = ""
    jazzcash_environment: str = "sandbox"  # sandbox | live

    # Easypaisa (Telenor Microfinance Bank) — Open Account / OTC + HMAC-SHA256
    # https://easypay.easypaisa.com.pk (Sandbox/Live differ by storeId range)
    easypaisa_store_id: str = ""
    easypaisa_hash_key: str = ""
    easypaisa_environment: str = "sandbox"

    # Meezan Bank Internet Payment Gateway — redirect + MD5/SHA-1 hash
    # Issued credentials come from Meezan's IPG onboarding pack.
    meezan_merchant_id: str = ""
    meezan_secret_key: str = ""
    meezan_environment: str = "sandbox"

    # Allied Bank — via 1LINK PayFast aggregator (covers ABL, HBL, UBL,
    # Bank Alfalah, etc. through a single integration). HMAC-SHA256.
    payfast_merchant_id: str = ""
    payfast_secret_key: str = ""
    payfast_environment: str = "sandbox"

    # SafePay — REST API (Bearer token, signed webhooks)
    # https://docs.getsafepay.com/
    safepay_api_key: str = ""
    safepay_webhook_secret: str = ""
    safepay_environment: str = "sandbox"

    # NayaPay — wallet API (Bearer token)
    nayapay_api_key: str = ""
    nayapay_webhook_secret: str = ""
    nayapay_environment: str = "sandbox"

    @field_validator("allowed_origins")
    @classmethod
    def parse_allowed_origins(cls, value: str) -> str:
        return value

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
