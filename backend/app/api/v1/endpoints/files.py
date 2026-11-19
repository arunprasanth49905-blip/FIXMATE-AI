from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.file import (
    FileCreateRequest,
    FileUpdateRequest,
    FileMetadata,
    FileContentResponse,
    FileTreeItem,
    FileUploadResponse,
)
from app.services.file_service import file_service

router = APIRouter(prefix="/projects/{project_id}", tags=["Files"])


@router.get("/files", response_model=Union[List[FileTreeItem], List[FileMetadata]])
def list_files(
    project_id: str,
    tree: bool = Query(False, description="Whether to return hierarchical tree structure"),
    db: Session = Depends(get_db),
):
    if tree:
        return file_service.get_project_file_tree(db, project_id)
    return file_service.get_project_files(db, project_id)


@router.post("/files", response_model=FileMetadata, status_code=status.HTTP_201_CREATED)
def create_file(
    project_id: str,
    data: FileCreateRequest,
    db: Session = Depends(get_db),
):
    return file_service.create_file_or_dir(
        db=db,
        project_id=project_id,
        path=data.path,
        content=data.content or "",
        is_directory=data.is_directory,
    )


@router.get("/files/{file_id}", response_model=FileContentResponse)
def get_file(
    project_id: str,
    file_id: str,
    db: Session = Depends(get_db),
):
    return file_service.get_file_content(db, project_id, file_id)


@router.put("/files/{file_id}", response_model=FileMetadata)
def save_file_content(
    project_id: str,
    file_id: str,
    data: FileUpdateRequest,
    db: Session = Depends(get_db),
):
    return file_service.save_file_content(
        db=db,
        project_id=project_id,
        file_id=file_id,
        content=data.content if data.content is not None else "",
    )


@router.patch("/files/{file_id}", response_model=FileMetadata)
def rename_or_move_file(
    project_id: str,
    file_id: str,
    data: FileUpdateRequest,
    db: Session = Depends(get_db),
):
    if not data.path:
        return file_service.get_file(db, project_id, file_id)
    return file_service.rename_or_move_file(
        db=db,
        project_id=project_id,
        file_id=file_id,
        new_path=data.path,
    )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    project_id: str,
    file_id: str,
    db: Session = Depends(get_db),
):
    file_service.delete_file_or_dir(db, project_id, file_id)
    return None


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    paths: Optional[List[str]] = Form(None),
    db: Session = Depends(get_db),
):
    uploaded, errors = await file_service.upload_files(
        db=db,
        project_id=project_id,
        files=files,
        paths=paths,
    )
    return FileUploadResponse(
        uploaded=[FileMetadata.model_validate(f) for f in uploaded],
        errors=errors,
    )
