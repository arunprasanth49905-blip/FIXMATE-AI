from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class VerificationCheck(BaseModel):
    name: str = Field(..., description="Unique check name (e.g. applied_integrity, syntax_verification)")
    status: Literal["passed", "failed", "warning", "skipped"] = Field(..., description="Status of this verification check")
    message: str = Field(..., description="Human-readable summary of the check result")
    details: Optional[str] = Field(None, description="Detailed evidence or syntax error location")


class FindingComparisonItem(BaseModel):
    id: Optional[str] = None
    rule_id: str
    rule_name: str
    severity: str
    category: Optional[str] = "correctness"
    file_path: str
    start_line: int
    start_column: Optional[int] = 1
    end_line: int
    end_column: Optional[int] = 1
    message: str
    evidence: Optional[str] = ""
    is_target: bool = False


class FindingsComparison(BaseModel):
    target_rule_id: str
    target_finding_status: Literal["resolved", "still_present", "inconclusive", "not_applicable"]
    before_count: int = 0
    after_count: int = 0
    resolved_count: int = 0
    regression_count: int = 0
    new_findings: List[FindingComparisonItem] = Field(default_factory=list)
    removed_findings: List[FindingComparisonItem] = Field(default_factory=list)
    unchanged_findings: List[FindingComparisonItem] = Field(default_factory=list)


class VerificationReportResponse(BaseModel):
    id: str
    project_id: str
    proposal_id: str
    file_path: str
    overall_status: Literal["verified", "failed", "partial", "inconclusive", "stale"]
    syntax_status: Literal["passed", "failed", "skipped"]
    target_bug_status: Literal["resolved", "still_present", "inconclusive", "not_applicable"]
    regression_status: Literal["passed", "warning", "failed"]
    pre_apply_fingerprint: str
    post_apply_fingerprint: str
    verified_fingerprint: str
    is_stale: bool
    checks: List[VerificationCheck]
    comparison: FindingsComparison
    error_message: Optional[str] = None
    duration_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationHistoryResponse(BaseModel):
    project_id: str
    proposal_id: str
    total: int
    verifications: List[VerificationReportResponse]


class VerificationListItem(VerificationReportResponse):
    project_name: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None


class VerificationOverviewMetrics(BaseModel):
    total_attempts: int = 0
    verified_count: int = 0
    failed_count: int = 0
    partial_count: int = 0
    inconclusive_count: int = 0
    stale_count: int = 0


class VerificationListResponse(BaseModel):
    items: List[VerificationListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    metrics: VerificationOverviewMetrics = Field(default_factory=VerificationOverviewMetrics)
