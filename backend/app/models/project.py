import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False, index=True)
    description = Column(Text, nullable=True)
    language = Column(String(50), nullable=False, default="python")
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Project {self.name} ({self.id})>"


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(500), nullable=False, index=True)  # Normalized relative path, e.g. "src/main.py"
    name = Column(String(255), nullable=False)
    is_directory = Column(Boolean, default=False, nullable=False)
    size = Column(Integer, default=0, nullable=False)
    extension = Column(String(50), default="", nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    project = relationship("Project", back_populates="files")

    __table_args__ = (
        UniqueConstraint("project_id", "path", name="uq_project_file_path"),
    )

    def __repr__(self):
        return f"<ProjectFile {self.path} (dir={self.is_directory})>"
