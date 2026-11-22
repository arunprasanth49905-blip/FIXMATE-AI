import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class SandboxExecution(Base):
    __tablename__ = "sandbox_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False, index=True)
    language = Column(String(50), nullable=False)
    execution_type = Column(String(32), nullable=False, default="code")  # "code" | "test"
    sandbox_runtime = Column(String(50), nullable=False, default="docker")
    status = Column(String(32), nullable=False, index=True)  # PASSED, FAILED, ERROR, TIMEOUT, CANCELLED, UNSUPPORTED, DEPENDENCIES_UNAVAILABLE, SANDBOX_UNAVAILABLE
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=False, default="")
    stderr = Column(Text, nullable=False, default="")
    runtime_error = Column(Text, nullable=True)
    timeout = Column(Boolean, nullable=False, default=False)
    duration_ms = Column(Float, nullable=False, default=0.0)
    start_time = Column(DateTime, nullable=False, default=get_utc_now)
    end_time = Column(DateTime, nullable=True)
    resource_limits_json = Column(Text, nullable=True)
    test_summary_json = Column(Text, nullable=True)
    cleanup_status = Column(String(32), nullable=False, default="cleaned")
    created_at = Column(DateTime, nullable=False, default=get_utc_now)

    project = relationship("Project", lazy="selectin")

    def __repr__(self):
        return f"<SandboxExecution {self.id} (project={self.project_id}, status={self.status})>"
