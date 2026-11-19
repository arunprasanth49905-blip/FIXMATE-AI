from pathlib import Path
from typing import Tuple, List, Optional
from app.core.config import settings


class ParserLimits:
    @staticmethod
    def is_excluded_path(rel_path: str, custom_excludes: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Checks if a file path is inside an excluded directory or should be omitted."""
        excludes = set(settings.PARSER_EXCLUDE_DIRS)
        if custom_excludes:
            excludes.update(custom_excludes)

        norm_path = rel_path.replace("\\", "/").strip("/")
        parts = [p.lower() for p in norm_path.split("/") if p]

        # Check directory segments
        for part in parts[:-1]:
            if part in excludes:
                return True, f"Excluded directory: {part}"

        # Sensitive file detection (never parse .env or secrets)
        filename = parts[-1] if parts else ""
        if filename.startswith(".env") or filename in [".gitignore", ".gitkeep"]:
            return True, f"Sensitive or configuration file: {filename}"

        return False, ""

    @staticmethod
    def validate_file_size(size_bytes: int) -> Tuple[bool, str]:
        """Enforces single file size limit."""
        if size_bytes > settings.MAX_PARSER_FILE_SIZE_BYTES:
            max_mb = settings.MAX_PARSER_FILE_SIZE_BYTES / (1024 * 1024)
            actual_mb = size_bytes / (1024 * 1024)
            return False, f"File size ({actual_mb:.2f} MB) exceeds maximum limit of {max_mb:.1f} MB"
        return True, ""

    @staticmethod
    def validate_project_limits(file_count: int, total_source_bytes: int) -> Tuple[bool, str]:
        """Enforces project-wide analysis limits."""
        if file_count > settings.MAX_FILES_PER_ANALYSIS:
            return False, f"Project contains {file_count} files, exceeding limit of {settings.MAX_FILES_PER_ANALYSIS}"
        if total_source_bytes > settings.MAX_TOTAL_ANALYSIS_SOURCE_BYTES:
            max_mb = settings.MAX_TOTAL_ANALYSIS_SOURCE_BYTES / (1024 * 1024)
            actual_mb = total_source_bytes / (1024 * 1024)
            return False, f"Total source volume ({actual_mb:.2f} MB) exceeds limit of {max_mb:.1f} MB"
        return True, ""
