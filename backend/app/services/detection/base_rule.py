import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.detection import Finding, FindingSeverity, FindingCategory, DetectionRuleInfo
from app.services.detection.rule_context import RuleContext


class BaseRule(ABC):
    """Abstract base class for all deterministic bug detection rules."""

    rule_id: str
    name: str
    language: str  # Python, JavaScript, TypeScript, or Multi
    severity: FindingSeverity
    confidence: float
    category: FindingCategory
    description: str
    remediation_guide: str
    version: str = "1.0.0"

    @abstractmethod
    def evaluate(self, context: RuleContext) -> List[Finding]:
        """Evaluates source code and syntax tree; returns zero or more findings."""
        pass

    def create_finding(
        self,
        context: RuleContext,
        start_line: int,
        start_column: int,
        end_line: int,
        end_column: int,
        message: str,
        explanation: Optional[str] = None,
        evidence: Optional[str] = None,
        remediation: Optional[str] = None,
        custom_severity: Optional[FindingSeverity] = None,
        custom_confidence: Optional[float] = None,
    ) -> Finding:
        """Helper to create a calibrated, schema-compliant Finding instance."""
        if evidence is None:
            evidence = context.extract_evidence(start_line, end_line)

        return Finding(
            id=str(uuid.uuid4()),
            project_id="",  # Injected by engine
            run_id=None,    # Injected by engine
            rule_id=self.rule_id,
            rule_name=self.name,
            language=context.language,
            severity=custom_severity or self.severity,
            confidence=custom_confidence or self.confidence,
            category=self.category,
            file_path=context.file_path,
            start_line=max(1, start_line),
            start_column=max(0, start_column),
            end_line=max(start_line, end_line),
            end_column=max(0, end_column),
            message=message,
            explanation=explanation or self.description,
            evidence=evidence,
            remediation=remediation or self.remediation_guide,
        )

    def to_info(self) -> DetectionRuleInfo:
        return DetectionRuleInfo(
            rule_id=self.rule_id,
            name=self.name,
            language=self.language,
            severity=self.severity,
            confidence=self.confidence,
            category=self.category,
            description=self.description,
            remediation_guide=self.remediation_guide,
            version=self.version,
        )
