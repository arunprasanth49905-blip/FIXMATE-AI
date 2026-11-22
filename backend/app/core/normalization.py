"""Centralized project name normalization and validation utilities for FIXMATE AI."""

from typing import Optional


class ProjectNameDuplicateError(Exception):
    """Raised when an operation would create or update a project with a duplicate normalized name."""

    def __init__(
        self,
        message: str = "Project name already exists. Choose a different project name.",
        conflict_name: str = "",
    ):
        self.message = message
        self.conflict_name = conflict_name
        super().__init__(self.message)


class ProjectValidationError(Exception):
    """Raised when project data fails basic validation."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


def normalize_project_name(name: Optional[str]) -> str:
    """
    Normalizes a project name for comparison and duplicate detection:
    - Trims leading and trailing whitespace.
    - Converts to lowercase (case-insensitive).
    - Replaces internal consecutive whitespace with a single space.
    """
    if not name or not isinstance(name, str):
        return ""
    # Strip leading/trailing whitespace and convert to lowercase
    trimmed = name.strip()
    return " ".join(trimmed.split()).lower()


def validate_project_name(name: Optional[str]) -> str:
    """
    Validates a project name:
    - Rejects empty, None, or whitespace-only strings.
    - Rejects names exceeding maximum length.
    - Returns the trimmed display name preserving user capitalization.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Project name cannot be empty or only whitespace")

    trimmed = name.strip()
    if not trimmed:
        raise ValueError("Project name cannot be empty or only whitespace")

    if len(trimmed) > 100:
        raise ValueError("Project name cannot exceed 100 characters")

    return trimmed
