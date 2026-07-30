from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    app_name: str = "PrintDrop"
    environment: str = "production"
    tz: str = Field(default="UTC", alias="TZ")
    database_url: str = Field(default="sqlite:///./printdrop.db", alias="DATABASE_URL")
    session_secret: str = Field(default="change-me", alias="SESSION_SECRET")
    print_api_key: str = Field(default="change-me", alias="PRINT_API_KEY")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123456", alias="ADMIN_PASSWORD")
    cups_server: str = Field(default="cups", alias="CUPS_SERVER")
    printer_name: str = Field(default="HP_LaserJet_M15w", alias="PRINTER_NAME")
    max_upload_mb: int = Field(default=20, alias="MAX_UPLOAD_MB")
    secure_cookies: bool = Field(default=False, alias="SECURE_COOKIES")
    cookie_samesite: str = "lax"
    csrf_token_ttl_seconds: int = 60 * 60 * 8
    print_status_poll_seconds: int = Field(default=30, alias="PRINT_STATUS_POLL_SECONDS")
    failed_file_retention_hours: int = Field(default=72, alias="FAILED_FILE_RETENTION_HOURS")
    pending_file_retention_days: int = Field(default=14, alias="PENDING_FILE_RETENTION_DAYS")
    session_max_age_seconds: int = Field(default=60 * 60 * 8, alias="SESSION_MAX_AGE_SECONDS")
    login_rate_limit_per_minute: int = Field(default=12, alias="LOGIN_RATE_LIMIT_PER_MINUTE")
    upload_rate_limit_per_minute: int = Field(default=30, alias="UPLOAD_RATE_LIMIT_PER_MINUTE")
    uploads_root: Path = Field(default=Path("/data/uploads"), alias="UPLOADS_ROOT")
    tmp_root: Path = Field(default=Path("/data/tmp"), alias="TMP_ROOT")
    retain_successful_uploads: bool = Field(default=False, alias="RETAIN_SUCCESSFUL_UPLOADS")
    force_password_change_default: bool = Field(default=True, alias="FORCE_PASSWORD_CHANGE_DEFAULT")
    run_scheduler: bool = Field(default=False, alias="RUN_SCHEDULER")
    web_port: int = Field(default=8000, alias="WEB_PORT")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    trusted_proxy_depth: int = Field(default=0, alias="TRUSTED_PROXY_DEPTH")
    allow_failed_job_retry: bool = Field(default=True, alias="ALLOW_FAILED_JOB_RETRY")
    max_job_retries: int = Field(default=3, alias="MAX_JOB_RETRIES")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
