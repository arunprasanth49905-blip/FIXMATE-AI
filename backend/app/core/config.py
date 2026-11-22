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
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
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

    # Phase 9: Secure Sandbox Execution Configuration
    SANDBOX_ENABLED: bool = True
    SANDBOX_DEFAULT_TIMEOUT_SECONDS: int = 10
    SANDBOX_MAX_TIMEOUT_SECONDS: int = 30
    SANDBOX_MAX_MEMORY_MB: int = 256
    SANDBOX_MAX_CPUS: float = 1.0
    SANDBOX_MAX_PIDS: int = 64
    SANDBOX_MAX_OUTPUT_BYTES: int = 1024 * 1024  # 1 MB per output stream
    SANDBOX_PYTHON_IMAGE: str = "python:3.13-slim"
    SANDBOX_JS_IMAGE: str = "node:20-slim"
    SANDBOX_STAGING_ROOT: str = "./data/sandbox_staging"

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

    def get_sandbox_staging_dir(self, execution_id: str) -> Path:
        base_dir = Path(self.SANDBOX_STAGING_ROOT).resolve()
        staging_dir = (base_dir / execution_id).resolve()
        if not staging_dir.is_relative_to(base_dir):
            raise ValueError("Invalid sandbox staging directory resolution")
        staging_dir.mkdir(parents=True, exist_ok=True)
        return staging_dir


settings = Settings()
