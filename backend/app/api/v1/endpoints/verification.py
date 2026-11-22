from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.verification import (
    VerificationReportResponse,
    VerificationHistoryResponse,
    VerificationListResponse,
)
from app.services.verification.verification_service import verification_service

router = APIRouter(tags=["Automated Repair Verification"])


@router.get(
    "/verification/history",
    response_model=VerificationListResponse,
    summary="List verification results across projects with metrics, filtering and pagination",
)
def list_verifications(
    project_id: Optional[str] = Query(None, description="Optional filter by project ID"),
    status: Optional[str] = Query(None, description="Optional filter by status (verified, failed, partial, stale, inconclusive)"),
    search: Optional[str] = Query(None, description="Optional search term matching file, project or rule"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
) -> VerificationListResponse:
    """
    Returns paginated verification records across all projects (or filtered by project)
    along with global/filtered verification overview metrics.
    """
    return verification_service.list_verifications(
        db=db,
        project_id=project_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/projects/{project_id}/verification-history",
    response_model=VerificationListResponse,
    summary="List verification results for a specific project",
)
def list_project_verifications(
    project_id: str,
    status: Optional[str] = Query(None, description="Optional filter by status"),
    search: Optional[str] = Query(None, description="Optional search term"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
) -> VerificationListResponse:
    """
    Returns paginated verification records for a specific project along with project verification metrics.
    """
    return verification_service.list_verifications(
        db=db,
        project_id=project_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/projects/{project_id}/repair/{proposal_id}/verify",
    response_model=VerificationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute automated static verification on an applied repair",
)
def verify_applied_repair(
    project_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
) -> VerificationReportResponse:
    """
    Executes Phase 8 Automated Verification & Repair Validation on an applied patch:
    - Integrity & anti-staleness check
    - Concrete AST/Tree-sitter syntax validation
    - Deterministic target bug resolution check
    - Static regression scan (zero user code execution)
    - Scope & fingerprint verification
    """
    return verification_service.verify_repair(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
    )


@router.get(
    "/projects/{project_id}/repair/{proposal_id}/verification-history",
    response_model=VerificationHistoryResponse,
    summary="Retrieve verification history for a repair proposal",
)
def get_repair_verification_history(
    project_id: str,
    proposal_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum verification records to return"),
    db: Session = Depends(get_db),
) -> VerificationHistoryResponse:
    """
    Retrieves chronological history of all automated verification runs for the repair proposal.
    """
    return verification_service.get_history(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
        limit=limit,
    )


@router.get(
    "/projects/{project_id}/verification/{verification_id}",
    response_model=VerificationReportResponse,
    summary="Retrieve a specific verification report by ID",
)
def get_verification_report(
    project_id: str,
    verification_id: str,
    db: Session = Depends(get_db),
) -> VerificationReportResponse:
    """
    Retrieves a single automated verification report.
    """
    return verification_service.get_verification_by_id(
        project_id=project_id,
        verification_id=verification_id,
        db=db,
    )
