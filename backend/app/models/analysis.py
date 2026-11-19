import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.session import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class ProjectAnalysis(Base):
    __tablename__ = "project_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="completed")  # completed, completed_with_diagnostics, failed, cancelled
    start_time = Column(DateTime, default=get_utc_now, nullable=False)
    end_time = Column(DateTime, default=get_utc_now, nullable=False)
    duration_ms = Column(Float, default=0.0, nullable=False)
    total_files = Column(Integer, default=0, nullable=False)
    parsed_files = Column(Integer, default=0, nullable=False)
    failed_files = Column(Integer, default=0, nullable=False)
    skipped_files = Column(Integer, default=0, nullable=False)
    statistics_json = Column(Text, nullable=False, default="{}")
    summary_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    project = relationship("Project", backref="analyses")
    file_records = relationship("FileAnalysisRecord", back_populates="analysis", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<ProjectAnalysis {self.id} (project={self.project_id}, status={self.status})>"


class FileAnalysisRecord(Base):
    __tablename__ = "file_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("project_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(String(36), nullable=True, index=True)
    file_path = Column(String(500), nullable=False, index=True)
    language = Column(String(50), nullable=False)
    parser_name = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)  # success, diagnostics, failed, skipped
    source_hash = Column(String(64), nullable=False)  # SHA-256
    source_size = Column(Integer, default=0, nullable=False)
    statistics_json = Column(Text, nullable=False, default="{}")
    symbols_json = Column(Text, nullable=False, default="[]")
    imports_json = Column(Text, nullable=False, default="[]")
    diagnostics_json = Column(Text, nullable=False, default="[]")
    structure_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    analysis = relationship("ProjectAnalysis", back_populates="file_records")

    __table_args__ = (
        Index("ix_file_analyses_analysis_path", "analysis_id", "file_path"),
    )

    def __repr__(self):
        return f"<FileAnalysisRecord {self.file_path} ({self.status})>"
