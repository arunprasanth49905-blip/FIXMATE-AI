from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: Optional[str] = Query(None, description="Search term for project name or description"),
    db: Session = Depends(get_db),
):
    projects = project_service.get_projects(db, search=search)
    project_responses = []
    for p in projects:
        file_count = project_service.get_project_file_count(db, p.id)
        project_responses.append(
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                language=p.language,
                created_at=p.created_at,
                updated_at=p.updated_at,
                file_count=file_count,
            )
        )
    return ProjectListResponse(total=len(project_responses), projects=project_responses)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = project_service.create_project(db, data)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        language=project.language,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=0,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    file_count = project_service.get_project_file_count(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        language=project.language,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=file_count,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, data: ProjectUpdate, db: Session = Depends(get_db)):
    project = project_service.update_project(db, project_id, data)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    file_count = project_service.get_project_file_count(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        language=project.language,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=file_count,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    deleted = project_service.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return None
