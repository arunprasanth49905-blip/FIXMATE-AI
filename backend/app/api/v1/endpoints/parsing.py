from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.schemas.parsing import (
    ParserStatusResponse,
    ProjectAnalysisResponse,
    FileAnalysis,
    SyntaxDiagnostic,
    ProjectParseRequest,
)
from app.services.parsing.parser_registry import parser_registry
from app.services.parsing.project_analysis_service import project_analysis_service

router = APIRouter(prefix="/projects/{project_id}/analysis", tags=["Code Intelligence & Parsing"])


def get_verified_project(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


@router.get("/parser-status", response_model=ParserStatusResponse)
def get_parser_status(project_id: str, db: Session = Depends(get_db)) -> ParserStatusResponse:
    """Returns engine readiness, language grammars, supported extensions, and limits."""
    get_verified_project(project_id, db)
    return parser_registry.get_status()


@router.post("/parse", response_model=ProjectAnalysisResponse, status_code=status.HTTP_201_CREATED)
def parse_project_codebase(
    project_id: str,
    request: Optional[ProjectParseRequest] = None,
    db: Session = Depends(get_db),
) -> ProjectAnalysisResponse:
    """Executes multi-language AST structural analysis across workspace files."""
    get_verified_project(project_id, db)
    try:
        return project_analysis_service.parse_project(db, project_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.get("/latest", response_model=ProjectAnalysisResponse)
def get_latest_project_analysis(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectAnalysisResponse:
    """Retrieves the most recent analysis report for this project."""
    get_verified_project(project_id, db)
    analysis = project_analysis_service.get_latest_analysis(db, project_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No previous analysis found for this project",
        )
    return analysis


@router.get("/parse/{analysis_id}", response_model=ProjectAnalysisResponse)
def get_analysis_by_id(
    project_id: str,
    analysis_id: str,
    db: Session = Depends(get_db),
) -> ProjectAnalysisResponse:
    """Retrieves a specific historical analysis record by its ID."""
    get_verified_project(project_id, db)
    analysis = project_analysis_service.get_analysis_by_id(db, project_id, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found",
        )
    return analysis


@router.get("/parse/{analysis_id}/files", response_model=List[FileAnalysis])
def get_analyzed_files(
    project_id: str,
    analysis_id: str,
    language: Optional[str] = Query(None, description="Filter by language"),
    parse_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
) -> List[FileAnalysis]:
    """Lists analyzed files with optional language and status filtering."""
    get_verified_project(project_id, db)
    analysis = project_analysis_service.get_analysis_by_id(db, project_id, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found",
        )

    results = analysis.files
    if language:
        results = [f for f in results if f.language.lower() == language.lower()]
    if parse_status:
        results = [f for f in results if f.status.lower() == parse_status.lower()]
    return results


@router.get("/parse/{analysis_id}/files/{file_id_or_path:path}", response_model=FileAnalysis)
def get_file_analysis_detail(
    project_id: str,
    analysis_id: str,
    file_id_or_path: str,
    db: Session = Depends(get_db),
) -> FileAnalysis:
    """Retrieves full symbols, imports, structure, and diagnostics for an analyzed file."""
    get_verified_project(project_id, db)
    analysis = project_analysis_service.get_analysis_by_id(db, project_id, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found",
        )

    for f in analysis.files:
        if f.file_id == file_id_or_path or f.file_path == file_id_or_path or f.file_path.endswith(file_id_or_path):
            return f

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"File '{file_id_or_path}' not found in analysis '{analysis_id}'",
    )


@router.get("/parse/{analysis_id}/diagnostics", response_model=List[SyntaxDiagnostic])
def get_analysis_diagnostics(
    project_id: str,
    analysis_id: str,
    db: Session = Depends(get_db),
) -> List[SyntaxDiagnostic]:
    """Retrieves all syntax diagnostics across files for an analysis."""
    get_verified_project(project_id, db)
    return project_analysis_service.get_diagnostics(db, project_id, analysis_id)
