from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.detection import DetectionFinding
from app.models.project import Project
from app.schemas.detection import (
    DetectionRuleInfo,
    DetectionRunResponse,
    FileDetectionRequest,
    Finding,
    FindingSeverity,
    FindingCategory,
    ProjectDetectionRequest,
)
from app.services.detection.detection_engine import detection_engine
from app.services.detection.rule_registry import rule_registry
from app.services.file_service import file_service
from app.services.parsing.parser_registry import parser_registry

router = APIRouter(prefix="/projects/{project_id}/detection", tags=["Deterministic Bug Detection"])


def get_verified_project(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


@router.get("/rules", response_model=List[DetectionRuleInfo])
def list_detection_rules(
    project_id: str,
    severity: Optional[FindingSeverity] = None,
    db: Session = Depends(get_db),
) -> List[DetectionRuleInfo]:
    """Returns catalog of all registered deterministic detection rules and metadata."""
    get_verified_project(project_id, db)
    return rule_registry.list_rules(severity=severity)


@router.post("/run", response_model=DetectionRunResponse, status_code=status.HTTP_201_CREATED)
def run_project_bug_detection(
    project_id: str,
    request: Optional[ProjectDetectionRequest] = None,
    db: Session = Depends(get_db),
) -> DetectionRunResponse:
    """Executes deterministic static bug detection across all supported project workspace files."""
    get_verified_project(project_id, db)
    try:
        return detection_engine.run_project_detection(db, project_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bug detection engine failure: {str(e)}",
        )


@router.post("/run-file", response_model=List[Finding])
def run_file_bug_detection(
    project_id: str,
    request: FileDetectionRequest,
    db: Session = Depends(get_db),
) -> List[Finding]:
    """Evaluates a single file or code snippet against deterministic bug rules."""
    get_verified_project(project_id, db)

    source_code = request.content
    if source_code is None:
        try:
            target_path, _ = file_service.sanitize_and_resolve_path(project_id, request.file_path)
            if not target_path.exists():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File does not exist")
            source_code = target_path.read_text(encoding="utf-8")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot read file: {e}")

    lang = request.language
    if not lang:
        parser = parser_registry.get_parser_for_path(request.file_path)
        lang = parser.language if parser else "Unknown"

    return detection_engine.evaluate_file(
        file_path=request.file_path,
        language=lang,
        source_code=source_code,
    )


@router.get("/latest", response_model=DetectionRunResponse)
def get_latest_detection_run(
    project_id: str,
    db: Session = Depends(get_db),
) -> DetectionRunResponse:
    """Retrieves the most recent static bug detection run and findings for the project."""
    get_verified_project(project_id, db)
    res = detection_engine.get_latest_run(db, project_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No bug detection runs found for this project",
        )
    return res


@router.get("/runs/{run_id}", response_model=DetectionRunResponse)
def get_detection_run(
    project_id: str,
    run_id: str,
    db: Session = Depends(get_db),
) -> DetectionRunResponse:
    """Retrieves a specific historical bug detection run."""
    get_verified_project(project_id, db)
    res = detection_engine.get_run_by_id(db, project_id, run_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection run '{run_id}' not found",
        )
    return res


@router.get("/runs/{run_id}/findings", response_model=List[Finding])
def get_detection_run_findings(
    project_id: str,
    run_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low, info"),
    language: Optional[str] = Query(None, description="Filter by language"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    search: Optional[str] = Query(None, description="Search keyword in message or explanation"),
    db: Session = Depends(get_db),
) -> List[Finding]:
    """Retrieves filtered findings for a specific detection run."""
    get_verified_project(project_id, db)

    query = db.query(DetectionFinding).filter(
        DetectionFinding.run_id == run_id,
        DetectionFinding.project_id == project_id,
    )

    if severity:
        query = query.filter(DetectionFinding.severity == severity.lower())
    if language:
        query = query.filter(DetectionFinding.language == language)
    if rule_id:
        query = query.filter(DetectionFinding.rule_id == rule_id)
    if category:
        query = query.filter(DetectionFinding.category == category.lower())
    if file_path:
        query = query.filter(DetectionFinding.file_path.ilike(f"%{file_path}%"))
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (DetectionFinding.message.ilike(search_term)) |
            (DetectionFinding.explanation.ilike(search_term))
        )

    db_findings = query.order_by(DetectionFinding.file_path, DetectionFinding.start_line).all()

    return [
        Finding(
            id=df.id,
            run_id=df.run_id,
            project_id=df.project_id,
            rule_id=df.rule_id,
            rule_name=df.rule_name,
            language=df.language,
            severity=FindingSeverity(df.severity),
            confidence=df.confidence,
            category=FindingCategory(df.category),
            file_path=df.file_path,
            start_line=df.start_line,
            start_column=df.start_column,
            end_line=df.end_line,
            end_column=df.end_column,
            message=df.message,
            explanation=df.explanation,
            evidence=df.evidence,
            remediation=df.remediation,
        )
        for df in db_findings
    ]
