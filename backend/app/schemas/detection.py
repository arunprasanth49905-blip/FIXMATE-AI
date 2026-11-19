from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    SUSPICIOUS = "suspicious"


class Finding(BaseModel):
    id: str
    run_id: Optional[str] = None
    project_id: str
    rule_id: str
    rule_name: str
    language: str
    severity: FindingSeverity
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: FindingCategory
    file_path: str
    start_line: int = Field(..., ge=1)
    start_column: int = Field(..., ge=0)
    end_line: int = Field(..., ge=1)
    end_column: int = Field(..., ge=0)
    message: str
    explanation: str
    evidence: str
    remediation: str


class DetectionRuleInfo(BaseModel):
    rule_id: str
    name: str
    language: str
    severity: FindingSeverity
    confidence: float
    category: FindingCategory
    description: str
    remediation_guide: str
    version: str = "1.0.0"


class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class DetectionRunSummary(BaseModel):
    run_id: str
    project_id: str
    analysis_id: Optional[str] = None
    status: str  # completed, completed_with_findings, failed
    engine_version: str
    created_at: str
    duration_ms: float
    files_scanned: int
    total_findings: int
    severity_counts: SeverityCounts
    findings_by_category: Dict[str, int] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class DetectionRunResponse(DetectionRunSummary):
    findings: List[Finding] = Field(default_factory=list)


class ProjectDetectionRequest(BaseModel):
    file_ids: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None
    rule_ids: Optional[List[str]] = None
    severities: Optional[List[FindingSeverity]] = None
    reuse_analysis: bool = True


class FileDetectionRequest(BaseModel):
    file_path: str
    content: Optional[str] = None
    language: Optional[str] = None
