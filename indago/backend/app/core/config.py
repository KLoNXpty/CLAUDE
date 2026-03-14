"""
INDAGO Evidence Capture Platform
Core Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import secrets


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "INDAGO Evidence Capture"
    APP_VERSION: str = "1.0.0"
    APP_TAGLINE: str = "Digital Evidence Preservation Platform"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://indago:indago_secret@localhost:5432/indago_db"
    DATABASE_URL_SYNC: str = "postgresql://indago:indago_secret@localhost:5432/indago_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Storage (S3-compatible)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "indago_access"
    S3_SECRET_KEY: str = "indago_secret_key"
    S3_BUCKET_EVIDENCE: str = "indago-evidence"
    S3_BUCKET_REPORTS: str = "indago-reports"
    S3_REGION: str = "us-east-1"

    # Evidence Storage
    EVIDENCE_BASE_PATH: str = "/evidence_storage"
    MAX_CAPTURE_SIZE_MB: int = 2048
    SCREENSHOT_FORMAT: str = "PNG"
    VIDEO_FORMAT: str = "webm"

    # Playwright / Capture
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    PAGE_LOAD_TIMEOUT_MS: int = 60000
    SCROLL_DELAY_MS: int = 500
    VIEWPORT_WIDTH: int = 1920
    VIEWPORT_HEIGHT: int = 1080
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # Forensics
    HASH_ALGORITHMS: List[str] = ["sha256", "sha512", "md5"]
    PRIMARY_HASH: str = "sha256"
    TSA_URL: str = "https://freetsa.org/tsr"  # RFC 3161 TSA
    ENABLE_BLOCKCHAIN_TIMESTAMP: bool = False
    OPENTIMESTAMPS_ENABLED: bool = False

    # PKI / Signing
    SIGNING_CERT_PATH: Optional[str] = None
    SIGNING_KEY_PATH: Optional[str] = None

    # Rate Limiting
    MAX_CONCURRENT_CAPTURES: int = 5
    RATE_LIMIT_PER_MINUTE: int = 10

    # Scheduler
    SCHEDULER_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
