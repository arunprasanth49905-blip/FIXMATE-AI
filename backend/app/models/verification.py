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


class RepairVerification(Base):
    """
    Stores an authoritative static verification report for an applied code repair.
    Phase 8: Evaluates syntax validity, target bug resolution, regression analysis,
    and change integrity without executing user code.
    """

    __tablename__ = "repair_verifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id = Column(String(36), ForeignKey("repair_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False, index=True)

    # Overall verification status: verified, failed, partial, inconclusive, stale
    status = Column(String(32), nullable=False, default="inconclusive", index=True)

    # Sub-check statuses
    syntax_status = Column(String(32), nullable=False, default="skipped")  # passed, failed, skipped
    target_bug_status = Column(String(32), nullable=False, default="inconclusive")  # resolved, still_present, inconclusive, not_applicable
    regression_status = Column(String(32), nullable=False, default="passed")  # passed, warning, failed

    # Cryptographic fingerprints
    pre_apply_fingerprint = Column(String(64), nullable=False)
    post_apply_fingerprint = Column(String(64), nullable=False)
    verified_fingerprint = Column(String(64), nullable=False)

    # Finding comparison metrics
    original_bug_count = Column(Integer, nullable=False, default=0)
    current_bug_count = Column(Integer, nullable=False, default=0)
    resolved_bug_count = Column(Integer, nullable=False, default=0)
    regression_bug_count = Column(Integer, nullable=False, default=0)

    # Detailed serialized payloads
    findings_comparison_json = Column(Text, nullable=False, default="{}")
    checks_details_json = Column(Text, nullable=False, default="[]")
    error_message = Column(Text, nullable=True)

    duration_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=get_utc_now, nullable=False, index=True)

    # Relationships
    project = relationship("Project", backref="repair_verifications")
    proposal = relationship("RepairProposal", backref="verifications")

    __table_args__ = (
        Index("ix_repair_verifications_proposal_created", "proposal_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RepairVerification id={self.id} proposal={self.proposal_id} status={self.status}>"
