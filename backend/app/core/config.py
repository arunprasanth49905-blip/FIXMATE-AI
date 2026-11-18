from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "FIXMATE AI"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_PORT: int = 8001
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # AI Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    SUPPORTED_LANGUAGES: List[str] = ["Python", "JavaScript"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
