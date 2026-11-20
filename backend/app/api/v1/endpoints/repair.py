from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.repair import (
    GenerateRepairRequest,
    RepairHistoryResponse,
    RepairProposalResponse,
    ApproveRepairResponse,
    RejectRepairResponse,
    ApplyRepairRequest,
    ApplyRepairResponse,
    RollbackRepairResponse,
    ProposalAuditHistoryResponse,
)
from app.services.repair.repair_service import RepairService
from app.services.repair.patch_application_service import PatchApplicationService

router = APIRouter()
repair_service = RepairService()
patch_application_service = PatchApplicationService()


@router.post(
    "/projects/{project_id}/repair/generate",
    response_model=RepairProposalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Code Repair"],
    summary="Generate targeted AI repair proposal and deterministic patch",
)
def generate_repair_proposal(
    project_id: str,
    payload: GenerateRepairRequest,
    db: Session = Depends(get_db),
) -> RepairProposalResponse:
    """
    Synthesizes a precise, minimal code repair proposal for a detected bug finding
    and its Root Cause Analysis using Gemini 3.5 Flash Lite.
    Deterministically computes and validates the unified diff without modifying files.
    """
    return repair_service.generate_repair(
        project_id=project_id,
        finding_id=payload.finding_id,
        db=db,
        custom_instructions=payload.custom_instructions,
    )


@router.get(
    "/projects/{project_id}/repair/history",
    response_model=RepairHistoryResponse,
    tags=["Code Repair"],
    summary="Retrieve repair proposal history for a project or finding",
)
def get_repair_history(
    project_id: str,
    finding_id: Optional[str] = Query(None, description="Filter history by finding ID"),
    limit: int = Query(20, ge=1, le=100, description="Max proposals to retrieve"),
    db: Session = Depends(get_db),
) -> RepairHistoryResponse:
    return repair_service.get_history(
        project_id=project_id,
        db=db,
        finding_id=finding_id,
        limit=limit,
    )


@router.get(
    "/projects/{project_id}/repair/finding/{finding_id}",
    response_model=Optional[RepairProposalResponse],
    tags=["Code Repair"],
    summary="Get the latest repair proposal for a specific bug finding",
)
def get_repair_for_finding(
    project_id: str,
    finding_id: str,
    db: Session = Depends(get_db),
) -> Optional[RepairProposalResponse]:
    return repair_service.get_latest_for_finding(
        project_id=project_id,
        finding_id=finding_id,
        db=db,
    )


@router.get(
    "/projects/{project_id}/repair/{proposal_id}",
    response_model=RepairProposalResponse,
    tags=["Code Repair"],
    summary="Get repair proposal by ID with real-time source staleness evaluation",
)
def get_repair_proposal(
    project_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
) -> RepairProposalResponse:
    return repair_service.get_proposal(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
    )


@router.delete(
    "/projects/{project_id}/repair/{proposal_id}",
    tags=["Code Repair"],
    summary="Discard a repair proposal record",
)
def delete_repair_proposal(
    project_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
):
    success = repair_service.delete_proposal(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
    )
    return {"deleted": success, "proposal_id": proposal_id}


# =========================================================================
# Phase 7: Human Approval, Controlled Patch Application & Rollback Endpoints
# =========================================================================

@router.post(
    "/projects/{project_id}/repair/{proposal_id}/approve",
    response_model=ApproveRepairResponse,
    tags=["Code Repair - Human Approval"],
    summary="Explicitly approve a repair proposal for application",
)
def approve_repair_proposal(
    project_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
) -> ApproveRepairResponse:
    """
    Validates preflight constraints (source freshness, patch reversibility, workspace bounds)
    and transitions the proposal to 'approved' state.
    """
    return patch_application_service.approve_proposal(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
    )


@router.post(
    "/projects/{project_id}/repair/{proposal_id}/reject",
    response_model=RejectRepairResponse,
    tags=["Code Repair - Human Approval"],
    summary="Explicitly reject a repair proposal",
)
def reject_repair_proposal(
    project_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
) -> RejectRepairResponse:
    """
    Rejects the proposal and permanently prevents it from being applied.
    """
    return patch_application_service.reject_proposal(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
    )


@router.post(
    "/projects/{project_id}/repair/{proposal_id}/apply",
    response_model=ApplyRepairResponse,
    tags=["Code Repair - Patch Application"],
    summary="Atomically apply an approved repair patch to disk source",
)
def apply_repair_patch(
    project_id: str,
    proposal_id: str,
    payload: ApplyRepairRequest = ApplyRepairRequest(confirm_application=True),
    db: Session = Depends(get_db),
) -> ApplyRepairResponse:
    """
    Controlled Patch Application:
    1. Preflight validation & fresh source SHA-256 matching.
    2. Byte-for-byte backup in project `.fixmate/backups/`.
    3. Atomic temporary-file write + replace.
    4. Post-write concrete AST syntax validation.
    5. Automatic failure recovery if post-write verification fails.
    """
    return patch_application_service.apply_patch(
        project_id=project_id,
        proposal_id=proposal_id,
        request=payload,
        db=db,
    )


@router.post(
    "/projects/{project_id}/repair/{proposal_id}/rollback",
    response_model=RollbackRepairResponse,
    tags=["Code Repair - Rollback"],
    summary="Revert an applied repair patch to the pre-application original source",
)
def rollback_repair_patch(
    project_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
) -> RollbackRepairResponse:
    """
    Rolls back an applied repair patch by restoring the exact original backup.
    Guarantees that if the file has been modified since application, rollback is blocked.
    """
    return patch_application_service.rollback_patch(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
    )


@router.get(
    "/projects/{project_id}/repair/{proposal_id}/audit-log",
    response_model=ProposalAuditHistoryResponse,
    tags=["Code Repair - Audit History"],
    summary="Retrieve full immutable audit log for a proposal",
)
def get_repair_audit_log(
    project_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
) -> ProposalAuditHistoryResponse:
    return patch_application_service.get_audit_history(
        project_id=project_id,
        proposal_id=proposal_id,
        db=db,
    )
