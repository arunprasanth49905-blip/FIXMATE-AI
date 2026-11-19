from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BugLocation(BaseModel):
    """Exact source code coordinate and metadata for a detected bug."""
    file: str = Field(..., description="File name or relative path where bug is located")
    line: int = Field(..., description="Exact line number of the buggy code")
    rule_id: str = Field(..., description="Bug rule identifier (e.g. PY-W007)")
    language: str = Field(..., description="Programming language of the source file")


class SeverityAssessment(BaseModel):
    """Dual-view severity comparison: authoritative static vs AI assessment."""
    detected_severity: str = Field(..., description="Authoritative severity determined by Phase 4 static engine")
    ai_assessed_severity: str = Field(..., description="AI suggested severity based on semantic reasoning")
    severity_reasoning: str = Field(..., description="Detailed explanation of AI severity judgment")
    severity_changed: bool = Field(False, description="Flag indicating if AI disagrees with static severity")


class ConfidenceAssessment(BaseModel):
    """Calibrated confidence breakdown with scoring, rationale, and limitations."""
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Calibrated confidence score between 0 and 100")
    confidence_level: str = Field("MEDIUM", description="Confidence category: HIGH, MEDIUM, or LOW")
    confidence_reason: str = Field(..., description="Explanation of why this confidence level was assigned")
    limitations: List[str] = Field(default_factory=list, description="Boundaries and constraints of static analysis")


class LLMRootCauseUpgradePayload(BaseModel):
    """Developer-friendly concise schema returned by Gemini for bug analysis and correction."""
    bug_summary: str = Field(..., description="Short summary of the bug, e.g. Division by zero")
    original_code: str = Field(..., description="The original buggy line(s) of source code")
    simple_explanation: str = Field(..., description="What went wrong explained in simple English for beginner developers")
    root_cause: str = Field(..., description="Exact root cause explaining why this code produces an error")
    corrected_code: str = Field(..., description="Gemini's suggested corrected code snippet")
    correction_explanation: str = Field(..., description="Short explanation of what changed and why it fixes the issue")
    assumptions: List[str] = Field(default_factory=list, description="Any assumptions made by AI about intent/logic")
    severity: str = Field("medium", description="critical | high | medium | low | info")
    severity_reasoning: Optional[str] = Field(None, description="Why this severity level applies")
    confidence: float = Field(90.0, ge=0.0, le=100.0, description="Confidence percentage 0-100")
    confidence_reason: Optional[str] = Field(None, description="Why this confidence was assigned")
    fix_status: str = Field("suggested_not_applied", description="suggested_not_applied | needs_clarification")


# Alias for backward compatibility if any internal callers use LLMRootCausePayload
LLMRootCausePayload = LLMRootCauseUpgradePayload


class RootCauseAnalysisResponse(BaseModel):
    """Full root cause analysis response for a detection finding."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    finding_id: str
    detection_run_id: Optional[str] = None
    rule_id: str
    rule_name: str
    language: str
    file_path: str
    start_line: int
    end_line: int
    model: str
    created_at: datetime
    duration_ms: float
    status: str

    # Upgraded Concise & Correction Fields
    bug_location: BugLocation
    original_code: str = Field(default="", description="Exact original buggy source code line")
    simple_explanation: str = Field(default="", description="Simple English explanation of what went wrong")
    corrected_code: str = Field(default="", description="Gemini's suggested corrected code block")
    correction_explanation: str = Field(default="", description="Short explanation of what changed and why")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions or uncertainties disclosed by AI")
    fix_status: str = Field(default="suggested_not_applied", description="suggested_not_applied or needs_clarification")

    # Core Investigation Fields (Backward-compatible)
    summary: str
    bug_explanation: str
    root_cause: str
    technical_reasoning: str
    trigger_conditions: List[str] = Field(default_factory=list)
    execution_impact: str
    potential_consequences: List[str] = Field(default_factory=list)

    severity_assessment: SeverityAssessment
    recommended_approach: str
    prevention: str
    missing_context: List[str] = Field(default_factory=list)

    confidence_assessment: ConfidenceAssessment
    error_message: Optional[str] = None


class AnalyzeFindingRequest(BaseModel):
    """Request payload to initiate an AI root cause analysis."""
    finding_id: str = Field(..., description="UUID of the detection finding to investigate")
    include_surrounding_context: bool = Field(True, description="Whether to include +/- 15 lines of context")
    custom_user_notes: Optional[str] = Field(None, max_length=1000, description="Optional developer notes or runtime observations")


class RootCauseHistoryItem(BaseModel):
    """Summary item for browsing root cause history."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    finding_id: str
    rule_id: str
    rule_name: str
    file_path: str
    start_line: int
    summary: str
    original_code: Optional[str] = ""
    corrected_code: Optional[str] = ""
    fix_status: Optional[str] = "suggested_not_applied"
    detected_severity: str
    ai_assessed_severity: str
    confidence_score: float
    confidence_level: str
    created_at: datetime
    duration_ms: float
    status: str


class RootCauseHistoryResponse(BaseModel):
    """Paginated or listed history of root cause analyses."""
    project_id: str
    total: int
    analyses: List[RootCauseHistoryItem]
