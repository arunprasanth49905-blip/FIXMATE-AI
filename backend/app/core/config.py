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
    SUPPORTED_LANGUAGES: List[str] = ["Python", "JavaScript", "TypeScript"]

    # Database & Storage Configuration
    DATABASE_URL: str = "sqlite:///./data/fixmate.db"
    WORKSPACE_ROOT: str = "./data/workspaces"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB per file

    # Phase 3: Parsing & Structural Intelligence Configuration
    MAX_PARSER_FILE_SIZE_BYTES: int = 1 * 1024 * 1024  # 1 MB max single file
    MAX_FILES_PER_ANALYSIS: int = 500                  # 500 files per project
    MAX_TOTAL_ANALYSIS_SOURCE_BYTES: int = 25 * 1024 * 1024  # 25 MB max total source
    PARSER_EXCLUDE_DIRS: List[str] = [
        "node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build",
        "coverage", ".next", ".vite", "vendor", ".pytest_cache"
    ]

    ALLOWED_EXTENSIONS: List[str] = [
        ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
        ".json", ".txt", ".md", ".markdown", ".css", ".scss", ".sass",
        ".html", ".htm", ".yaml", ".yml", ".toml", ".sql", ".sh", ".bash",
        ".env.example", ".xml", ".csv", ".ini", ".cfg", ".conf", ".gitignore"
    ]

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
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
