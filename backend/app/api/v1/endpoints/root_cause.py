from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.root_cause import (
    AnalyzeFindingRequest,
    RootCauseAnalysisResponse,
    RootCauseHistoryResponse,
)
from app.services.root_cause.root_cause_service import RootCauseService

router = APIRouter(prefix="/projects/{project_id}/root-cause", tags=["AI Root Cause Analysis"])

root_cause_service = RootCauseService()


@router.post("/analyze", response_model=RootCauseAnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze_finding_root_cause(
    project_id: str,
    request: AnalyzeFindingRequest,
    db: Session = Depends(get_db),
) -> RootCauseAnalysisResponse:
    """
    Executes AI Root Cause Analysis on an authoritative deterministic bug finding.
    Returns deep technical explanation, root cause breakdown, consequences,
    severity review, and conceptual remediation strategy.
    """
    return root_cause_service.analyze_finding(db=db, project_id=project_id, request=request)


@router.get("/latest", response_model=RootCauseAnalysisResponse)
def get_latest_project_analysis(
    project_id: str,
    db: Session = Depends(get_db),
) -> RootCauseAnalysisResponse:
    """Retrieves the most recent AI Root Cause Analysis report for this project."""
    return root_cause_service.get_latest_analysis(db=db, project_id=project_id)


@router.get("/history", response_model=RootCauseHistoryResponse)
def get_root_cause_history(
    project_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of historical analyses to return"),
    db: Session = Depends(get_db),
) -> RootCauseHistoryResponse:
    """Retrieves list of past AI Root Cause Analyses performed on this project."""
    return root_cause_service.get_history(db=db, project_id=project_id, limit=limit)


@router.get("/finding/{finding_id}", response_model=Optional[RootCauseAnalysisResponse])
def get_analysis_for_finding(
    project_id: str,
    finding_id: str,
    db: Session = Depends(get_db),
) -> Optional[RootCauseAnalysisResponse]:
    """Retrieves the latest AI Root Cause Analysis for a specific detection finding, or null if unanalyzed."""
    return root_cause_service.get_analysis_for_finding(db=db, project_id=project_id, finding_id=finding_id)


@router.get("/{analysis_id}", response_model=RootCauseAnalysisResponse)
def get_root_cause_analysis_by_id(
    project_id: str,
    analysis_id: str,
    db: Session = Depends(get_db),
) -> RootCauseAnalysisResponse:
    """Retrieves a specific root cause analysis report by its unique ID."""
    return root_cause_service.get_analysis(db=db, project_id=project_id, analysis_id=analysis_id)


@router.delete("/{analysis_id}", status_code=status.HTTP_200_OK)
def delete_root_cause_analysis(
    project_id: str,
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Deletes an existing root cause analysis report."""
    root_cause_service.delete_analysis(db=db, project_id=project_id, analysis_id=analysis_id)
    return {"deleted": True, "analysis_id": analysis_id}
