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
    Phase 7 extends this with human approval, controlled application lifecycle,
    and rollback tracking.
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

    # Lifecycle state machine: proposed, approved, rejected, applying, applied, failed, rolled_back, stale
    # (Phase 6 legacy "generated" maps cleanly to "proposed")
    repair_status = Column(String(32), nullable=False, default="proposed", index=True)

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

    # Phase 7: Approval and Application Lifecycle Metadata
    approval_status = Column(String(32), nullable=False, default="pending", index=True)  # pending, approved, rejected
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    rollback_at = Column(DateTime, nullable=True)
    rollback_status = Column(String(32), nullable=True)  # rolled_back, failed

    backup_id = Column(String(36), nullable=True)
    backup_path = Column(String(512), nullable=True)
    pre_apply_fingerprint = Column(String(64), nullable=True)
    post_apply_fingerprint = Column(String(64), nullable=True)
    apply_attempt_id = Column(String(36), nullable=True)
    apply_error = Column(Text, nullable=True)
    post_validation_details_json = Column(Text, nullable=True)

    # Metadata & Telemetry
    model = Column(String(64), nullable=False)
    duration_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=get_utc_now, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", backref="repair_proposals")
    finding = relationship("DetectionFinding", backref="repair_proposals")
    root_cause = relationship("RootCauseAnalysis", backref="repair_proposals")
    backups = relationship("RepairBackup", back_populates="proposal", cascade="all, delete-orphan")
    audit_logs = relationship("RepairAuditLog", back_populates="proposal", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_repair_project_created", "project_id", "created_at"),
        Index("ix_repair_finding_created", "finding_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RepairProposal id={self.id} finding={self.finding_id} status={self.repair_status}>"


class RepairBackup(Base):
    """
    Stores an authoritative pre-application backup of a source file
    prior to modifying the file on disk during Phase 7 controlled patch application.
    """

    __tablename__ = "repair_backups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id = Column(String(36), ForeignKey("repair_proposals.id", ondelete="CASCADE"), nullable=False, index=True)

    file_path = Column(String(512), nullable=False)
    backup_file_path = Column(String(512), nullable=False)
    original_content = Column(Text, nullable=False)
    original_fingerprint = Column(String(64), nullable=False)

    status = Column(String(32), nullable=False, default="active", index=True)  # active, restored_on_failure, rolled_back
    created_at = Column(DateTime, default=get_utc_now, nullable=False, index=True)
    restored_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", backref="repair_backups")
    proposal = relationship("RepairProposal", back_populates="backups")

    def __repr__(self) -> str:
        return f"<RepairBackup id={self.id} proposal={self.proposal_id} file={self.file_path}>"


class RepairAuditLog(Base):
    """
    Stores an immutable audit trail of every lifecycle event in the
    proposal -> approval -> application -> rollback workflow.
    """

    __tablename__ = "repair_audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id = Column(String(36), ForeignKey("repair_proposals.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(64), nullable=False, index=True)
    target_file = Column(String(512), nullable=False)
    source_fingerprint = Column(String(64), nullable=True)
    details_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=get_utc_now, nullable=False, index=True)

    # Relationships
    project = relationship("Project", backref="repair_audit_logs")
    proposal = relationship("RepairProposal", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<RepairAuditLog id={self.id} event={self.event_type} proposal={self.proposal_id}>"
