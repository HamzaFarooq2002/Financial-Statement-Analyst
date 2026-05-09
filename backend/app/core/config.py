from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AI Financial Report Analyst API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./financial_agent.db"
    upload_dir: Path = Path("./uploads")
    export_dir: Path = Path("./exports")
    max_upload_mb: int = Field(default=50, ge=1)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    cors_origin_regex: str = r"^http://(localhost|127\.0\.0\.1):\d+$"
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    gemini_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: float = Field(default=45, ge=5)
    gemini_max_retries: int = Field(
        default=5,
        ge=0,
        description="429/quota backoff: retries after the first attempt (total attempts = 1 + this value).",
    )
    gemini_retry_base_seconds: float = Field(default=2.0, ge=0.5)
    gemini_retry_max_delay_seconds: float = Field(default=60.0, ge=1.0)
    gemini_http_sdk_retries: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Low-level HTTP retries inside google-genai (small number avoids thundering herd on 429).",
    )
    processing_timeout_seconds: int = Field(default=300, ge=30)

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("database_url")
    @classmethod
    def resolve_sqlite_database_url(cls, value: str) -> str:
        sqlite_prefix = "sqlite:///"
        if not value.startswith(sqlite_prefix) or value.startswith("sqlite:////"):
            return value

        database_path = value.removeprefix(sqlite_prefix)
        if database_path == ":memory:":
            return value

        path = Path(database_path)
        if path.is_absolute():
            return value
        return sqlite_prefix + (BACKEND_DIR / path).resolve().as_posix()

    @field_validator("upload_dir", "export_dir")
    @classmethod
    def resolve_backend_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return (BACKEND_DIR / value).resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
