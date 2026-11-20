from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    name: str
    status: str = Field(description="passed, failed, or warning")
    message: str
    details: Optional[str] = None


class PatchValidationDetails(BaseModel):
    checks: List[ValidationCheck] = Field(default_factory=list)
    overall_status: str = Field(default="passed", description="passed, failed, or warning")
    is_syntactically_valid: bool = True
    is_reversible: bool = True
    is_scope_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)


class GenerateRepairRequest(BaseModel):
    finding_id: str
    custom_instructions: Optional[str] = None


class LLMRepairPayload(BaseModel):
    """Structured response contract expected from Gemini repair generation."""
    repair_summary: str
    repair_explanation: str
    original_code: str
    proposed_code: str
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = Field(default=90.0, ge=0.0, le=100.0)
    repair_status: str = Field(default="generated", description="generated or needs_clarification")


class RepairProposalResponse(BaseModel):
    id: str
    project_id: str
    finding_id: str
    root_cause_analysis_id: Optional[str] = None

    rule_id: str
    rule_name: str
    language: str
    file_path: str
    start_line: int
    end_line: int

    source_fingerprint: str
    is_stale: bool = Field(default=False, description="True if disk file has changed since generation")

    # Lifecycle state: proposed, approved, rejected, applying, applied, failed, rolled_back, stale
    repair_status: str
    repair_summary: str
    repair_explanation: str
    original_code: str
    proposed_code: str

    diff: str
    additions: int
    deletions: int

    assumptions: List[str] = Field(default_factory=list)
    confidence_score: float

    validation_status: str  # passed, failed, warning
    validation_details: PatchValidationDetails

    # Phase 7: Approval & Application metadata
    approval_status: str = Field(default="pending", description="pending, approved, rejected")
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None
    applied_at: Optional[str] = None
    rollback_at: Optional[str] = None
    rollback_status: Optional[str] = None

    backup_id: Optional[str] = None
    backup_path: Optional[str] = None
    pre_apply_fingerprint: Optional[str] = None
    post_apply_fingerprint: Optional[str] = None
    apply_attempt_id: Optional[str] = None
    apply_error: Optional[str] = None
    post_validation_details: Optional[PatchValidationDetails] = None

    model: str
    duration_ms: float
    created_at: str
    error_message: Optional[str] = None


class RepairHistoryResponse(BaseModel):
    project_id: str
    total: int
    proposals: List[RepairProposalResponse]


# =========================================================================
# Phase 7: Approval, Controlled Application & Rollback Schemas
# =========================================================================

class ApproveRepairResponse(BaseModel):
    proposal_id: str
    project_id: str
    status: str = "approved"
    approved_at: str
    source_fingerprint: str
    message: str = "Repair proposal approved successfully."


class RejectRepairResponse(BaseModel):
    proposal_id: str
    project_id: str
    status: str = "rejected"
    rejected_at: str
    message: str = "Repair proposal rejected."


class ApplyRepairRequest(BaseModel):
    confirm_application: bool = Field(True, description="Explicit human confirmation required to modify disk source")
    comment: Optional[str] = None


class ApplyRepairResponse(BaseModel):
    proposal_id: str
    project_id: str
    file_path: str
    status: str = Field(description="applied or failed")
    applied_at: Optional[str] = None
    backup_id: Optional[str] = None
    backup_path: Optional[str] = None
    pre_apply_fingerprint: str
    post_apply_fingerprint: Optional[str] = None
    syntax_validation_passed: bool
    additions: int
    deletions: int
    message: str
    error: Optional[str] = None
    recovery_attempted: bool = False
    recovery_succeeded: bool = False


class RollbackRepairResponse(BaseModel):
    proposal_id: str
    project_id: str
    file_path: str
    status: str = "rolled_back"
    rollback_at: str
    restored_fingerprint: str
    message: str = "Repair patch rolled back successfully. Original source restored."


class AuditLogEntry(BaseModel):
    id: str
    proposal_id: str
    event_type: str
    target_file: str
    source_fingerprint: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ProposalAuditHistoryResponse(BaseModel):
    proposal_id: str
    project_id: str
    total_events: int
    events: List[AuditLogEntry]
