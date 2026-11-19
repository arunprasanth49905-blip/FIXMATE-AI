from pathlib import Path
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

    # Database & Storage Configuration
    DATABASE_URL: str = "sqlite:///./data/fixmate.db"
    WORKSPACE_ROOT: str = "./data/workspaces"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB per file

    ALLOWED_EXTENSIONS: List[str] = [
        ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
        ".json", ".txt", ".md", ".markdown", ".css", ".scss", ".sass",
        ".html", ".htm", ".yaml", ".yml", ".toml", ".sql", ".sh", ".bash",
        ".env.example", ".xml", ".csv", ".ini", ".cfg", ".conf", ".gitignore"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_workspace_dir(self, project_id: str) -> Path:
        base_dir = Path(self.WORKSPACE_ROOT).resolve()
        project_dir = (base_dir / project_id).resolve()
        # Enforce that project directory is always strictly within workspace root
        if not project_dir.is_relative_to(base_dir):
            raise ValueError("Invalid project workspace directory resolution")
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir


settings = Settings()
