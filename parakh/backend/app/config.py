from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PARAKH API"
    api_prefix: str = "/api"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "parakh"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "parakh-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    default_bid_validity_days: int = 180
    ocr_confidence_threshold: float = 0.75
    upload_root: Path = Path(__file__).resolve().parent / "uploads"
    fixtures_root: Path = Path(__file__).resolve().parent / "fixtures"
    audit_export_root: Path = Path(__file__).resolve().parent / "uploads" / "audit_exports"
    demo_admin_username: str = "admin"
    demo_admin_password: str = "admin123"
    demo_officer_username: str = "officer"
    demo_officer_password: str = "officer123"
    cors_origins: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_root.mkdir(parents=True, exist_ok=True)
    (settings.upload_root / "tenders").mkdir(parents=True, exist_ok=True)
    (settings.upload_root / "bidders").mkdir(parents=True, exist_ok=True)
    settings.audit_export_root.mkdir(parents=True, exist_ok=True)
    return settings
