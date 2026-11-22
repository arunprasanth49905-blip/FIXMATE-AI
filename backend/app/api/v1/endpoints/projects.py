from typing import Optional
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.normalization import (
    ProjectNameDuplicateError,
    normalize_project_name,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    DuplicateAuditResponse,
    DuplicateProjectGroup,
)
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: Optional[str] = Query(None, description="Search term for project name or description"),
    db: Session = Depends(get_db),
):
    projects = project_service.get_projects(db, search=search)

    # Compute duplicate normalized names across all returned projects
    norm_counts = Counter(
        p.normalized_name or normalize_project_name(p.name) for p in projects
    )

    project_responses = []
    for p in projects:
        norm = p.normalized_name or normalize_project_name(p.name)
        file_count = project_service.get_project_file_count(db, p.id)
        project_responses.append(
            ProjectResponse(
                id=p.id,
                name=p.name,
                normalized_name=norm,
                description=p.description,
                language=p.language,
                created_at=p.created_at,
                updated_at=p.updated_at,
                file_count=file_count,
                is_duplicate=(norm_counts[norm] > 1),
            )
        )
    return ProjectListResponse(total=len(project_responses), projects=project_responses)


@router.get("/duplicates/audit", response_model=DuplicateAuditResponse)
def audit_duplicate_projects(db: Session = Depends(get_db)):
    """
    Audits existing projects in the database for duplicate normalized names.
    Reports conflict groups, project IDs, names, and languages without modifying any records.
    """
    audit_data = project_service.audit_duplicate_projects(db)
    groups = []
    for norm_name, projs in audit_data["groups"].items():
        proj_responses = []
        for p in projs:
            file_count = project_service.get_project_file_count(db, p.id)
            proj_responses.append(
                ProjectResponse(
                    id=p.id,
                    name=p.name,
                    normalized_name=norm_name,
                    description=p.description,
                    language=p.language,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    file_count=file_count,
                    is_duplicate=True,
                )
            )
        groups.append(
            DuplicateProjectGroup(
                normalized_name=norm_name,
                count=len(projs),
                projects=proj_responses,
            )
        )

    return DuplicateAuditResponse(
        total_duplicate_groups=audit_data["total_duplicate_groups"],
        total_duplicate_projects=audit_data["total_duplicate_projects"],
        groups=groups,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    try:
        project = project_service.create_project(db, data)
    except ProjectNameDuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        normalized_name=project.normalized_name,
        description=project.description,
        language=project.language,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=0,
        is_duplicate=False,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    file_count = project_service.get_project_file_count(db, project.id)
    norm = project.normalized_name or normalize_project_name(project.name)

    # Check if duplicate exists
    dup = project_service.find_project_by_normalized_name(db, norm, exclude_project_id=project.id)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        normalized_name=norm,
        description=project.description,
        language=project.language,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=file_count,
        is_duplicate=(dup is not None),
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, data: ProjectUpdate, db: Session = Depends(get_db)):
    try:
        project = project_service.update_project(db, project_id, data)
    except ProjectNameDuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    file_count = project_service.get_project_file_count(db, project.id)
    norm = project.normalized_name or normalize_project_name(project.name)
    dup = project_service.find_project_by_normalized_name(db, norm, exclude_project_id=project.id)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        normalized_name=norm,
        description=project.description,
        language=project.language,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=file_count,
        is_duplicate=(dup is not None),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    deleted = project_service.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return None
