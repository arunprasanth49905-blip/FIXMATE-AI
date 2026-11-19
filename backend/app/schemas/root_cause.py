from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


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


class LLMRootCausePayload(BaseModel):
    """Schema expected directly from Gemini JSON output."""
    summary: str = Field(..., description="Brief one-line summary of finding")
    bug_explanation: str = Field(..., description="What the bug actually is in plain developer terms")
    root_cause: str = Field(..., description="The fundamental underlying flaw")
    technical_reasoning: str = Field(..., description="Deep architectural and language-level reasoning")
    trigger_conditions: List[str] = Field(default_factory=list, description="Specific conditions under which the bug manifests")
    execution_impact: str = Field(..., description="How the bug alters runtime behavior and state")
    potential_consequences: List[str] = Field(default_factory=list, description="Concrete failure modes or security implications")
    ai_assessed_severity: str = Field("medium", description="AI assessed severity: critical, high, medium, low, info")
    severity_reasoning: str = Field(..., description="Reasoning for AI severity assessment")
    recommended_approach: str = Field(..., description="Conceptual and architectural remediation guidance (no code patches)")
    prevention: str = Field(..., description="Best practices, linting, or testing strategies to prevent recurrence")
    missing_context: List[str] = Field(default_factory=list, description="Missing project files or runtime inputs")
    confidence_score: float = Field(80.0, ge=0.0, le=100.0, description="Confidence score 0-100")
    confidence_level: str = Field("HIGH", description="Confidence level HIGH, MEDIUM, LOW")
    confidence_reason: str = Field(..., description="Justification for confidence score")
    limitations: List[str] = Field(default_factory=list, description="Known limitations of this static analysis")


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
