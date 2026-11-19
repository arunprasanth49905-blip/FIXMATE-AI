import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
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


class RepairProposal(Base):
    """
    Stores an intelligent code repair proposal and deterministic patch
    generated for a detected bug finding and Root Cause Analysis.
    Preserves original source code without applying changes (Phase 6 boundary).
    """

    __tablename__ = "repair_proposals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(String(36), ForeignKey("detection_findings.id", ondelete="CASCADE"), nullable=False, index=True)
    root_cause_analysis_id = Column(String(36), ForeignKey("root_cause_analyses.id", ondelete="SET NULL"), nullable=True, index=True)

    rule_id = Column(String(32), nullable=False, index=True)
    rule_name = Column(String(128), nullable=False)
    language = Column(String(64), nullable=False)
    file_path = Column(String(512), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    # SHA-256 fingerprint of the original file at proposal generation time
    source_fingerprint = Column(String(64), nullable=False)

    # Status: generated, needs_clarification, rejected_by_validation, stale_source, generation_failed
    repair_status = Column(String(32), nullable=False, default="generated", index=True)

    # Detailed AI Repair Proposal Content
    repair_summary = Column(Text, nullable=False, default="")
    repair_explanation = Column(Text, nullable=False, default="")
    original_code = Column(Text, nullable=False, default="")
    proposed_code = Column(Text, nullable=False, default="")

    # Deterministic Server-Generated Unified Diff & Metrics
    diff = Column(Text, nullable=False, default="")
    additions = Column(Integer, nullable=False, default=0)
    deletions = Column(Integer, nullable=False, default=0)

    # AI Assumptions & Confidence
    assumptions_json = Column(Text, nullable=False, default="[]")
    confidence_score = Column(Float, nullable=False, default=0.0)

    # Deterministic Validation Results
    validation_status = Column(String(32), nullable=False, default="passed", index=True)  # passed, failed, warning
    validation_details_json = Column(Text, nullable=False, default="{}")

    # Metadata & Telemetry
    model = Column(String(64), nullable=False)
    duration_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=get_utc_now, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", backref="repair_proposals")
    finding = relationship("DetectionFinding", backref="repair_proposals")
    root_cause = relationship("RootCauseAnalysis", backref="repair_proposals")

    __table_args__ = (
        Index("ix_repair_project_created", "project_id", "created_at"),
        Index("ix_repair_finding_created", "finding_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RepairProposal id={self.id} finding={self.finding_id} status={self.repair_status}>"
