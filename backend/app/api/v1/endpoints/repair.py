from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.repair import (
    GenerateRepairRequest,
    RepairHistoryResponse,
    RepairProposalResponse,
)
from app.services.repair.repair_service import RepairService

router = APIRouter()
repair_service = RepairService()


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
