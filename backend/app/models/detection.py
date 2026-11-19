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


class DetectionRun(Base):
    """Stores metadata and summary metrics for a static bug detection execution."""

    __tablename__ = "detection_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(String(36), ForeignKey("project_analyses.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(32), nullable=False, default="completed")  # completed, completed_with_findings, failed
    engine_version = Column(String(32), nullable=False, default="1.0.0")
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    duration_ms = Column(Float, nullable=False, default=0.0)
    files_scanned = Column(Integer, nullable=False, default=0)
    total_findings = Column(Integer, nullable=False, default=0)

    # Pre-aggregated severity counts for high-performance dashboard queries
    critical_count = Column(Integer, nullable=False, default=0)
    high_count = Column(Integer, nullable=False, default=0)
    medium_count = Column(Integer, nullable=False, default=0)
    low_count = Column(Integer, nullable=False, default=0)
    info_count = Column(Integer, nullable=False, default=0)

    # Detailed aggregations
    findings_by_severity_json = Column(Text, nullable=False, default="{}")
    findings_by_category_json = Column(Text, nullable=False, default="{}")
    warnings_json = Column(Text, nullable=False, default="[]")

    # Relationships
    project = relationship("Project", backref="detection_runs")
    analysis = relationship("ProjectAnalysis", backref="detection_runs")
    findings = relationship("DetectionFinding", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DetectionRun id={self.id} project_id={self.project_id} findings={self.total_findings}>"


class DetectionFinding(Base):
    """Stores an individual deterministic bug detection finding with code evidence and remediation."""

    __tablename__ = "detection_findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("detection_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    rule_id = Column(String(32), nullable=False, index=True)
    rule_name = Column(String(128), nullable=False)
    language = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)  # critical, high, medium, low, info
    confidence = Column(Float, nullable=False, default=0.90)
    category = Column(String(64), nullable=False, index=True)  # correctness, security, performance, maintainability, suspicious

    file_path = Column(String(512), nullable=False, index=True)
    start_line = Column(Integer, nullable=False)
    start_column = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    end_column = Column(Integer, nullable=False)

    message = Column(String(512), nullable=False)
    explanation = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)

    # Relationship
    run = relationship("DetectionRun", back_populates="findings")

    __table_args__ = (
        Index("ix_detection_findings_project_severity", "project_id", "severity"),
        Index("ix_detection_findings_run_severity", "run_id", "severity"),
    )

    def __repr__(self) -> str:
        return f"<DetectionFinding id={self.id} rule={self.rule_id} file={self.file_path}:{self.start_line}>"
