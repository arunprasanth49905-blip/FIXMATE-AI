import re
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.services.file_service import FileService

file_service = FileService()

# Security redaction patterns for API keys, tokens, and secrets
SECRET_PATTERNS = [
    # Gemini API keys (AIza followed by 35 or more chars)
    (re.compile(r"AIza[0-9A-Za-z-_]{35,}", re.IGNORECASE), "[REDACTED_GEMINI_KEY]"),
    # GitHub personal access tokens
    (re.compile(r"gh[pous]_[A-Za-z0-9_]{35,}", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
    # Generic Bearer tokens
    (re.compile(r"bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # Private Key blocks
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
    # AWS Access Key IDs
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Hardcoded secrets/passwords assignments: password="xyz", api_key='abc' (skip if already redacted)
    (re.compile(r"""(?i)(['"]?(?:api[_-]?key|secret|token|password|passwd|auth[_-]?token)['"]?\s*[:=]\s*['"])(?!\[REDACTED)([^'"]{4,})(['"])"""), r"\g<1>[REDACTED]\g<3>"),
]


def redact_sensitive_data(text: str) -> str:
    """Sanitizes source code to ensure secrets, passwords, or tokens are not forwarded to LLMs."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class RootCauseContextBuilder:
    """
    Safely reads source files from the workspace, extracts finding code coordinates
    with surrounding lines, applies secret redactions, formats with line numbers,
    and enforces token/character safety caps.
    """

    MAX_SNIPPET_CHARS = 8000
    DEFAULT_PADDING = 15

    @classmethod
    def build_finding_context(
        cls,
        project_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        padding: int = DEFAULT_PADDING,
    ) -> str:
        """
        Reads source file, extracts [start_line - padding, end_line + padding],
        applies line numbering, redact secrets, and marks untrusted content boundaries.
        """
        try:
            target_path, clean_rel = file_service.sanitize_and_resolve_path(project_id, file_path)
            if not target_path.is_file():
                return f"[Warning: Source file '{file_path}' does not exist on disk]"

            raw_code = target_path.read_text(encoding="utf-8", errors="replace")
            lines = raw_code.splitlines()

            total_lines = len(lines)
            if total_lines == 0:
                return "[Warning: Source file is empty]"

            # 1-indexed to 0-indexed slicing with padding
            from_line = max(1, start_line - padding)
            to_line = min(total_lines, end_line + padding)

            formatted_lines = []
            for line_idx in range(from_line, to_line + 1):
                actual_line = lines[line_idx - 1]
                # Mark target finding lines with an indicator
                is_finding_line = start_line <= line_idx <= end_line
                marker = ">>>" if is_finding_line else "   "
                formatted_lines.append(f"{marker} {line_idx:4d} | {actual_line}")

            snippet = "\n".join(formatted_lines)
            # Redact secrets
            safe_snippet = redact_sensitive_data(snippet)

            # Cap character length
            if len(safe_snippet) > cls.MAX_SNIPPET_CHARS:
                safe_snippet = safe_snippet[: cls.MAX_SNIPPET_CHARS] + "\n... [Context truncated for length] ..."

            return safe_snippet

        except Exception as e:
            logger.warning("Failed to extract finding context for %s (%s): %s", file_path, project_id, e)
            return f"[Error loading context for {file_path}: {str(e)}]"

    @classmethod
    def extract_exact_error_line(
        cls,
        project_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> str:
        """
        Extracts the exact source code line(s) between start_line and end_line
        without line numbers or markers, with secrets redacted.
        Returns line unavailable message if not found or out of bounds.
        """
        try:
            target_path, clean_rel = file_service.sanitize_and_resolve_path(project_id, file_path)
            if not target_path.is_file():
                return "[Error line location unavailable: file not found on disk]"

            raw_code = target_path.read_text(encoding="utf-8", errors="replace")
            lines = raw_code.splitlines()
            total_lines = len(lines)

            if total_lines == 0 or start_line < 1 or start_line > total_lines:
                return "[Error line location unavailable]"

            to_line = min(total_lines, max(start_line, end_line))
            target_slice = lines[start_line - 1 : to_line]
            raw_target = "\n".join(target_slice).strip()
            return redact_sensitive_data(raw_target)
        except Exception as e:
            logger.warning("Failed to extract exact error line for %s:%d: %s", file_path, start_line, e)
            return "[Error line location unavailable]"

