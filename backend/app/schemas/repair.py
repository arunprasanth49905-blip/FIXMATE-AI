from datetime import datetime
from typing import List, Optional
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

    repair_status: str  # generated, needs_clarification, rejected_by_validation, stale_source, generation_failed
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

    model: str
    duration_ms: float
    created_at: str
    error_message: Optional[str] = None


class RepairHistoryResponse(BaseModel):
    project_id: str
    total: int
    proposals: List[RepairProposalResponse]
