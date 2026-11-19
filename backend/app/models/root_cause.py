import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RootCauseAnalysis(Base):
    """Stores the structured AI-powered root cause analysis result for a detection finding."""

    __tablename__ = "root_cause_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(String(36), ForeignKey("detection_findings.id", ondelete="CASCADE"), nullable=False, index=True)
    detection_run_id = Column(String(36), ForeignKey("detection_runs.id", ondelete="SET NULL"), nullable=True, index=True)

    rule_id = Column(String(32), nullable=False, index=True)
    rule_name = Column(String(128), nullable=False)
    language = Column(String(64), nullable=False)
    file_path = Column(String(512), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    model = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False, index=True)
    duration_ms = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="success")  # success, failed

    # Core Investigation
    summary = Column(Text, nullable=False, default="")
    bug_explanation = Column(Text, nullable=False, default="")
    root_cause = Column(Text, nullable=False, default="")
    technical_reasoning = Column(Text, nullable=False, default="")
    trigger_conditions_json = Column(Text, nullable=False, default="[]")
    execution_impact = Column(Text, nullable=False, default="")
    potential_consequences_json = Column(Text, nullable=False, default="[]")

    # Severity Assessment (Dual view)
    detected_severity = Column(String(32), nullable=False)  # Authoritative Phase 4 severity
    ai_assessed_severity = Column(String(32), nullable=False)  # AI suggested severity
    severity_reasoning = Column(Text, nullable=False, default="")
    severity_changed = Column(Boolean, nullable=False, default=False)

    # Actionable guidance (Strictly no code patches)
    recommended_approach = Column(Text, nullable=False, default="")
    prevention = Column(Text, nullable=False, default="")
    missing_context_json = Column(Text, nullable=False, default="[]")

    # Calibrated confidence
    confidence_score = Column(Float, nullable=False, default=0.0)  # 0 to 100
    confidence_level = Column(String(16), nullable=False, default="MEDIUM")  # HIGH, MEDIUM, LOW
    confidence_reason = Column(Text, nullable=False, default="")
    limitations_json = Column(Text, nullable=False, default="[]")

    # Raw telemetry & error
    raw_response = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", backref="root_cause_analyses")
    finding = relationship("DetectionFinding", backref="root_cause_analyses")
    run = relationship("DetectionRun", backref="root_cause_analyses")

    __table_args__ = (
        Index("ix_root_cause_project_created", "project_id", "created_at"),
        Index("ix_root_cause_finding_created", "finding_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RootCauseAnalysis id={self.id} finding={self.finding_id} rule={self.rule_id}>"
