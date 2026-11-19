from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class FileCreateRequest(BaseModel):
    path: str = Field(..., description="Relative path in project, e.g. 'src/main.py' or 'utils'")
    content: Optional[str] = Field("", description="Initial text content for file")
    is_directory: bool = Field(False, description="Whether this is a directory")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("File path cannot be empty")
        if trimmed.startswith("/") or trimmed.startswith("\\") or ":" in trimmed:
            raise ValueError("Absolute paths, drive letters, and leading slashes are not permitted")
        normalized = trimmed.replace("\\", "/")
        parts = normalized.split("/")
        if any(p == ".." or p == "." or not p for p in parts):
            raise ValueError("Path traversal ('..') or invalid segments are strictly prohibited")
        return normalized


class FileUpdateRequest(BaseModel):
    content: Optional[str] = Field(None, description="Updated file content")
    path: Optional[str] = Field(None, description="New relative path for rename/move")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("New file path cannot be empty")
            if trimmed.startswith("/") or trimmed.startswith("\\") or ":" in trimmed:
                raise ValueError("Absolute paths, drive letters, and leading slashes are not permitted")
            normalized = trimmed.replace("\\", "/")
            parts = normalized.split("/")
            if any(p == ".." or p == "." or not p for p in parts):
                raise ValueError("Path traversal ('..') or invalid segments are strictly prohibited")
            return normalized
        return v


class FileMetadata(BaseModel):
    id: str
    project_id: str
    path: str
    name: str
    is_directory: bool
    size: int
    extension: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FileContentResponse(FileMetadata):
    content: Optional[str] = None
    is_binary: bool = False


class FileTreeItem(BaseModel):
    id: str
    path: str
    name: str
    is_directory: bool
    size: int
    extension: str
    children: Optional[List["FileTreeItem"]] = None


class FileUploadResponse(BaseModel):
    uploaded: List[FileMetadata]
    errors: List[str] = []
