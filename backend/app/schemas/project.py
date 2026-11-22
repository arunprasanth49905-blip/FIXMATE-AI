from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.core.normalization import validate_project_name, normalize_project_name


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    language: str = Field("python", description="Primary programming language")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_project_name(v)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        valid_languages = ["python", "javascript", "typescript", "general"]
        lower = v.strip().lower()
        if lower not in valid_languages:
            return "general"
        return lower


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    language: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_project_name(v)
        return v


class ProjectResponse(ProjectBase):
    id: str
    normalized_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    is_duplicate: bool = False

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    total: int
    projects: List[ProjectResponse]


class DuplicateProjectGroup(BaseModel):
    normalized_name: str
    count: int
    projects: List[ProjectResponse]


class DuplicateAuditResponse(BaseModel):
    total_duplicate_groups: int
    total_duplicate_projects: int
    groups: List[DuplicateProjectGroup]
