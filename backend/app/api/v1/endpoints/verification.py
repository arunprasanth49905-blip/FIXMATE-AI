from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.verification import (
    VerificationReportResponse,
    VerificationHistoryResponse,
)
from app.services.verification.verification_service import verification_service

router = APIRouter(tags=["Automated Repair Verification"])


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
