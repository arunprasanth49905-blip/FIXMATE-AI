import json
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.logging import logger
from app.models.repair import RepairProposal
from app.schemas.repair import (
    PatchValidationDetails,
    RepairHistoryResponse,
    RepairProposalResponse,
    ValidationCheck,
)
from app.services.file_service import FileService
from app.services.repair.patch_generator import PatchGenerator
from app.services.repair.patch_validator import PatchValidator
from app.services.repair.repair_context import (
    RepairContextBuilder,
    compute_source_fingerprint,
)
from app.services.repair.repair_engine import RepairEngine

file_service = FileService()


class RepairService:
    """
    Main business orchestration service for Phase 6 Intelligent Code Repair.
    Coordinates context extraction, AI repair generation, deterministic patch building,
    multi-layer validation, and database persistence.
    """

    def __init__(self, engine: Optional[RepairEngine] = None):
        self.engine = engine or RepairEngine()

    def _to_response_dto(self, record: RepairProposal, is_stale: bool = False) -> RepairProposalResponse:
        assumptions: List[str] = []
        try:
            assumptions = json.loads(record.assumptions_json or "[]")
        except Exception:
            pass

        validation_data = {
            "checks": [],
            "overall_status": record.validation_status,
            "is_syntactically_valid": True,
            "is_reversible": True,
            "is_scope_valid": True,
            "validation_errors": [],
        }
        try:
            if record.validation_details_json:
                validation_data = json.loads(record.validation_details_json)
        except Exception:
            pass

        checks = [
            ValidationCheck(
                name=c.get("name", "Check"),
                status=c.get("status", "passed"),
                message=c.get("message", ""),
                details=c.get("details"),
            )
            for c in validation_data.get("checks", [])
        ]

        validation_details = PatchValidationDetails(
            checks=checks,
            overall_status=validation_data.get("overall_status", record.validation_status),
            is_syntactically_valid=validation_data.get("is_syntactically_valid", True),
            is_reversible=validation_data.get("is_reversible", True),
            is_scope_valid=validation_data.get("is_scope_valid", True),
            validation_errors=validation_data.get("validation_errors", []),
        )

        return RepairProposalResponse(
            id=record.id,
            project_id=record.project_id,
            finding_id=record.finding_id,
            root_cause_analysis_id=record.root_cause_analysis_id,
            rule_id=record.rule_id,
            rule_name=record.rule_name,
            language=record.language,
            file_path=record.file_path,
            start_line=record.start_line,
            end_line=record.end_line,
            source_fingerprint=record.source_fingerprint,
            is_stale=is_stale,
            repair_status=record.repair_status,
            repair_summary=record.repair_summary,
            repair_explanation=record.repair_explanation,
            original_code=record.original_code,
            proposed_code=record.proposed_code,
            diff=record.diff,
            additions=record.additions,
            deletions=record.deletions,
            assumptions=assumptions,
            confidence_score=record.confidence_score,
            validation_status=record.validation_status,
            validation_details=validation_details,
            model=record.model,
            duration_ms=record.duration_ms,
            created_at=record.created_at.isoformat() if record.created_at else "",
            error_message=record.error_message,
        )

    def _check_source_staleness(self, project_id: str, file_path: str, stored_fingerprint: str) -> bool:
        """Compares current file content on disk to stored fingerprint."""
        try:
            target_path, _ = file_service.sanitize_and_resolve_path(project_id, file_path)
            if not target_path.is_file():
                return True
            current_content = target_path.read_text(encoding="utf-8", errors="replace")
            current_fp = compute_source_fingerprint(current_content)
            return current_fp != stored_fingerprint
        except Exception:
            return True

    def generate_repair(
        self,
        project_id: str,
        finding_id: str,
        db: Session,
        custom_instructions: Optional[str] = None,
    ) -> RepairProposalResponse:
        # 1. Build and validate repair context
        context = RepairContextBuilder.build_context(project_id, finding_id, db)

        # Handle stale source before AI generation
        if context.is_stale:
            record = RepairProposal(
                project_id=project_id,
                finding_id=finding_id,
                root_cause_analysis_id=context.rca_id,
                rule_id=context.rule_id,
                rule_name=context.rule_name,
                language=context.language,
                file_path=context.file_path,
                start_line=context.start_line,
                end_line=context.end_line,
                source_fingerprint=context.source_fingerprint,
                repair_status="stale_source",
                repair_summary="Source file has changed since bug detection.",
                repair_explanation=context.staleness_reason or "Source file does not match finding coordinate.",
                original_code=context.exact_original_code,
                proposed_code="",
                diff="",
                additions=0,
                deletions=0,
                assumptions_json="[]",
                confidence_score=0.0,
                validation_status="failed",
                validation_details_json=json.dumps({
                    "checks": [{
                        "name": "Source Freshness",
                        "status": "failed",
                        "message": context.staleness_reason or "Source file mismatch.",
                    }],
                    "overall_status": "failed",
                    "validation_errors": [context.staleness_reason or "Source file mismatch."],
                }),
                model=self.engine.model,
                duration_ms=0.0,
                error_message=context.staleness_reason,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return self._to_response_dto(record, is_stale=True)

        # 2. Invoke Gemini 3.5 Flash Lite
        llm_payload, duration_ms, raw_text = self.engine.generate_repair(context, custom_instructions)

        # 3. Construct targeted patch deterministically
        patch_artifact = PatchGenerator.generate_patch(
            full_source_raw=context.full_source_raw,
            start_line=context.start_line,
            end_line=context.end_line,
            proposed_code=llm_payload.proposed_code,
            file_path=context.file_path,
        )

        # 4. Validate patch deterministically
        validation = PatchValidator.validate_patch(
            file_path=context.file_path,
            language=context.language,
            original_source=context.full_source_raw,
            repaired_source=patch_artifact.repaired_source,
            start_line=context.start_line,
            end_line=context.end_line,
            source_fingerprint=context.source_fingerprint,
            expected_fingerprint=compute_source_fingerprint(context.full_source_raw),
        )

        # 5. Determine repair status
        repair_status = "generated"
        if llm_payload.repair_status == "needs_clarification":
            repair_status = "needs_clarification"
        elif validation.overall_status == "failed":
            repair_status = "rejected_by_validation"

        # 6. Persist proposal to SQLite
        record = RepairProposal(
            project_id=project_id,
            finding_id=finding_id,
            root_cause_analysis_id=context.rca_id,
            rule_id=context.rule_id,
            rule_name=context.rule_name,
            language=context.language,
            file_path=context.file_path,
            start_line=context.start_line,
            end_line=context.end_line,
            source_fingerprint=context.source_fingerprint,
            repair_status=repair_status,
            repair_summary=llm_payload.repair_summary,
            repair_explanation=llm_payload.repair_explanation,
            original_code=llm_payload.original_code or context.exact_original_code,
            proposed_code=llm_payload.proposed_code,
            diff=patch_artifact.diff,
            additions=patch_artifact.additions,
            deletions=patch_artifact.deletions,
            assumptions_json=json.dumps(llm_payload.assumptions),
            confidence_score=llm_payload.confidence,
            validation_status=validation.overall_status,
            validation_details_json=json.dumps(validation.model_dump()),
            model=self.engine.model,
            duration_ms=duration_ms,
            error_message="; ".join(validation.validation_errors) if validation.validation_errors else None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            "Phase 6 Repair proposal %s generated for finding %s (%s) in %.1fms with status %s",
            record.id, finding_id, context.rule_id, duration_ms, repair_status
        )

        return self._to_response_dto(record, is_stale=False)

    def get_proposal(self, project_id: str, proposal_id: str, db: Session) -> RepairProposalResponse:
        proposal = db.get(RepairProposal, proposal_id)
        if not proposal or proposal.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repair proposal '{proposal_id}' not found in project '{project_id}'.",
            )
        is_stale = self._check_source_staleness(project_id, proposal.file_path, proposal.source_fingerprint)
        return self._to_response_dto(proposal, is_stale=is_stale)

    def get_latest_for_finding(self, project_id: str, finding_id: str, db: Session) -> Optional[RepairProposalResponse]:
        query = (
            select(RepairProposal)
            .where(
                RepairProposal.project_id == project_id,
                RepairProposal.finding_id == finding_id,
            )
            .order_by(desc(RepairProposal.created_at))
        )
        proposal = db.execute(query).scalars().first()
        if not proposal:
            return None
        is_stale = self._check_source_staleness(project_id, proposal.file_path, proposal.source_fingerprint)
        return self._to_response_dto(proposal, is_stale=is_stale)

    def get_history(
        self,
        project_id: str,
        db: Session,
        finding_id: Optional[str] = None,
        limit: int = 20,
    ) -> RepairHistoryResponse:
        query = select(RepairProposal).where(RepairProposal.project_id == project_id)
        if finding_id:
            query = query.where(RepairProposal.finding_id == finding_id)
        query = query.order_by(desc(RepairProposal.created_at)).limit(min(100, max(1, limit)))

        proposals = db.execute(query).scalars().all()
        dtos = [
            self._to_response_dto(
                p,
                is_stale=self._check_source_staleness(project_id, p.file_path, p.source_fingerprint),
            )
            for p in proposals
        ]
        return RepairHistoryResponse(
            project_id=project_id,
            total=len(dtos),
            proposals=dtos,
        )

    def delete_proposal(self, project_id: str, proposal_id: str, db: Session) -> bool:
        proposal = db.get(RepairProposal, proposal_id)
        if not proposal or proposal.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repair proposal '{proposal_id}' not found in project '{project_id}'.",
            )
        db.delete(proposal)
        db.commit()
        return True
