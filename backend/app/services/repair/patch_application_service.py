import os
import ast
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.project import Project, ProjectFile
from app.models.repair import RepairProposal, RepairBackup, RepairAuditLog
from app.schemas.repair import (
    ApproveRepairResponse,
    RejectRepairResponse,
    ApplyRepairRequest,
    ApplyRepairResponse,
    RollbackRepairResponse,
    AuditLogEntry,
    ProposalAuditHistoryResponse,
    PatchValidationDetails,
    ValidationCheck,
)
from app.services.file_service import FileService
from app.services.repair.patch_generator import PatchGenerator
from app.services.repair.patch_validator import PatchValidator
from app.services.repair.repair_context import compute_source_fingerprint
from app.services.parsing.parser_registry import ParserRegistry

file_service = FileService()
parser_registry = ParserRegistry()


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PatchApplicationService:
    """
    Controlled Patch Application Engine (Phase 7).
    This service is the ONLY component in FIXMATE AI authorized to modify user source
    files on disk, and only after explicit human approval and preflight validation.
    """

    def _get_proposal_and_verify_project(
        self, project_id: str, proposal_id: str, db: Session
    ) -> Tuple[Project, RepairProposal]:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )

        proposal = db.get(RepairProposal, proposal_id)
        if not proposal or proposal.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repair proposal '{proposal_id}' not found in project '{project_id}'.",
            )

        return project, proposal

    def _record_audit_log(
        self,
        db: Session,
        project_id: str,
        proposal_id: str,
        event_type: str,
        target_file: str,
        source_fingerprint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> RepairAuditLog:
        log_entry = RepairAuditLog(
            project_id=project_id,
            proposal_id=proposal_id,
            event_type=event_type,
            target_file=target_file,
            source_fingerprint=source_fingerprint,
            details_json=json.dumps(details or {}),
            created_at=get_utc_now(),
        )
        db.add(log_entry)
        return log_entry

    def _verify_applied_content(self, clean_path: str, applied_content: str, language: str) -> None:
        """Runs concrete AST syntax validation on patched source file content."""
        lang = language.lower()
        if "python" in lang or clean_path.endswith((".py", ".pyw")):
            try:
                ast.parse(applied_content, filename=clean_path)
            except SyntaxError as e:
                raise ValueError(f"Python SyntaxError: {e.msg} at line {e.lineno}")
        elif any(clean_path.endswith(ext) for ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
            parser = parser_registry.get_parser_for_path(clean_path)
            if parser:
                parse_res = parser.parse(clean_path, applied_content)
                if parse_res.diagnostics:
                    raise ValueError(f"JavaScript/TypeScript parse errors: {'; '.join(d.message for d in parse_res.diagnostics)}")

    # =========================================================================
    # STEP 4: Human Approval & Rejection APIs
    # =========================================================================

    def approve_proposal(
        self, project_id: str, proposal_id: str, db: Session
    ) -> ApproveRepairResponse:
        """
        Validates pre-conditions and moves a proposal to the 'approved' state.
        Must verify source freshness, workspace confinement, and patch validity.
        """
        project, proposal = self._get_proposal_and_verify_project(project_id, proposal_id, db)

        # State machine check: only proposed/generated proposals can be approved
        current_status = proposal.repair_status.lower()
        if current_status in ("applied", "applying"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot approve a proposal that has already been applied.",
            )
        if current_status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve a rejected proposal. Please generate a new proposal.",
            )
        if current_status == "rolled_back":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve a rolled-back proposal. A new proposal must be generated.",
            )
        if current_status not in ("proposed", "generated", "approved"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state transition: cannot approve proposal in '{current_status}' state.",
            )

        # Workspace path security
        target_path, clean_path = file_service.sanitize_and_resolve_path(project_id, proposal.file_path)
        if not target_path.is_file():
            proposal.repair_status = "stale"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target source file '{proposal.file_path}' no longer exists on disk.",
            )

        # Cryptographic Staleness Check
        disk_content = target_path.read_text(encoding="utf-8", errors="replace")
        current_fp = compute_source_fingerprint(disk_content)
        if current_fp != proposal.source_fingerprint:
            proposal.repair_status = "stale"
            self._record_audit_log(
                db, project_id, proposal_id, "stale_detected", proposal.file_path, current_fp,
                {"reason": "Disk source modified before approval", "expected": proposal.source_fingerprint, "current": current_fp}
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="STALE PROPOSAL: Source file has been modified on disk since this patch was generated. Please regenerate the repair.",
            )

        # In-memory patch revalidation
        patch_artifact = PatchGenerator.generate_patch(
            full_source_raw=disk_content,
            start_line=proposal.start_line,
            end_line=proposal.end_line,
            proposed_code=proposal.proposed_code,
            file_path=clean_path,
        )

        validation = PatchValidator.validate_patch(
            file_path=clean_path,
            language=proposal.language,
            original_source=disk_content,
            repaired_source=patch_artifact.repaired_source,
            start_line=proposal.start_line,
            end_line=proposal.end_line,
            source_fingerprint=current_fp,
            expected_fingerprint=proposal.source_fingerprint,
        )

        if not validation.is_syntactically_valid or not validation.is_reversible or not validation.is_scope_valid:
            proposal.repair_status = "failed"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Patch revalidation failed prior to approval: {'; '.join(validation.validation_errors)}",
            )

        # Apply approval state transition
        now = get_utc_now()
        proposal.repair_status = "approved"
        proposal.approval_status = "approved"
        proposal.approved_at = now
        proposal.error_message = None

        self._record_audit_log(
            db, project_id, proposal_id, "approved", proposal.file_path, current_fp,
            {"approved_at": now.isoformat(), "fingerprint": current_fp}
        )

        db.commit()
        logger.info("Proposal %s approved for project %s", proposal_id, project_id)

        return ApproveRepairResponse(
            proposal_id=proposal_id,
            project_id=project_id,
            status="approved",
            approved_at=now.isoformat(),
            source_fingerprint=current_fp,
            message="Repair proposal approved successfully and ready for controlled application.",
        )

    def reject_proposal(
        self, project_id: str, proposal_id: str, db: Session
    ) -> RejectRepairResponse:
        """
        Rejects a repair proposal. A rejected proposal cannot be applied.
        """
        project, proposal = self._get_proposal_and_verify_project(project_id, proposal_id, db)

        current_status = proposal.repair_status.lower()
        if current_status in ("applied", "applying"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot reject a proposal that has already been applied. Use rollback instead.",
            )

        now = get_utc_now()
        proposal.repair_status = "rejected"
        proposal.approval_status = "rejected"
        proposal.rejected_at = now

        self._record_audit_log(
            db, project_id, proposal_id, "rejected", proposal.file_path, proposal.source_fingerprint,
            {"rejected_at": now.isoformat()}
        )

        db.commit()
        logger.info("Proposal %s rejected for project %s", proposal_id, project_id)

        return RejectRepairResponse(
            proposal_id=proposal_id,
            project_id=project_id,
            status="rejected",
            rejected_at=now.isoformat(),
            message="Repair proposal rejected. Patch will not be applied to source.",
        )

    # =========================================================================
    # STEP 5 & 6: Controlled Patch Application & Failure Recovery
    # =========================================================================

    def apply_patch(
        self, project_id: str, proposal_id: str, request: ApplyRepairRequest, db: Session
    ) -> ApplyRepairResponse:
        """
        Atomically applies an approved repair proposal to the target file on disk.
        Preflight -> Backup -> In-memory Synthesis -> Atomic Write -> Post-verification -> Recovery on failure.
        """
        if not request.confirm_application:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Human confirmation is required to modify disk files (confirm_application must be true).",
            )

        project, proposal = self._get_proposal_and_verify_project(project_id, proposal_id, db)

        # 1. State machine preflight: MUST BE APPROVED
        current_status = proposal.repair_status.lower()
        if current_status == "applied":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Proposal has already been applied. Duplicate application is prevented.",
            )
        if current_status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot apply a rejected proposal. Please generate and approve a new proposal.",
            )
        if current_status in ("proposed", "generated"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approval Required: This proposal has not been approved yet. Call /approve first.",
            )
        if current_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot apply proposal in '{current_status}' state.",
            )

        # 2. Path Security & Workspace Confinement
        target_path, clean_path = file_service.sanitize_and_resolve_path(project_id, proposal.file_path)
        if not target_path.is_file():
            proposal.repair_status = "stale"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target file '{proposal.file_path}' no longer exists on disk.",
            )

        # Symlink check
        if target_path.is_symlink():
            real_target = target_path.resolve()
            workspace_dir = settings.get_workspace_dir(project_id).resolve()
            if not real_target.is_relative_to(workspace_dir):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Security violation: target file is a symlink escaping project workspace.",
                )

        # 3. Cryptographic Staleness Protection
        original_disk_content = target_path.read_text(encoding="utf-8", errors="replace")
        current_fp = compute_source_fingerprint(original_disk_content)
        if current_fp != proposal.source_fingerprint:
            proposal.repair_status = "stale"
            self._record_audit_log(
                db, project_id, proposal_id, "stale_detected", proposal.file_path, current_fp,
                {"reason": "Disk source changed before application", "expected": proposal.source_fingerprint, "current": current_fp}
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="STALE PROPOSAL: Target file has been modified on disk since proposal approval. Application aborted.",
            )

        # 4. In-Memory Synthesis & Pre-write Verification
        patch_artifact = PatchGenerator.generate_patch(
            full_source_raw=original_disk_content,
            start_line=proposal.start_line,
            end_line=proposal.end_line,
            proposed_code=proposal.proposed_code,
            file_path=clean_path,
        )
        repaired_source = patch_artifact.repaired_source

        # Pre-write validation
        pre_val = PatchValidator.validate_patch(
            file_path=clean_path,
            language=proposal.language,
            original_source=original_disk_content,
            repaired_source=repaired_source,
            start_line=proposal.start_line,
            end_line=proposal.end_line,
            source_fingerprint=current_fp,
            expected_fingerprint=proposal.source_fingerprint,
        )

        if not pre_val.is_syntactically_valid or not pre_val.is_reversible or not pre_val.is_scope_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Patch validation failed prior to disk write: {'; '.join(pre_val.validation_errors)}",
            )

        # 5. Create Byte-for-Byte Authoritative Backup
        backup_dir = settings.get_workspace_dir(project_id) / ".fixmate" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_id = str(uuid.uuid4())
        backup_file_name = f"{proposal_id}_{int(get_utc_now().timestamp())}_{backup_id[:8]}.bak"
        backup_path = backup_dir / backup_file_name

        try:
            # Write exact original bytes
            raw_orig_bytes = target_path.read_bytes()
            backup_path.write_bytes(raw_orig_bytes)
        except Exception as e:
            logger.error("Failed to write backup before patch application: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Backup creation failed before applying patch: {str(e)}",
            )

        # Verify backup integrity
        backup_fp = compute_source_fingerprint(backup_path.read_text(encoding="utf-8", errors="replace"))
        if backup_fp != current_fp:
            backup_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Backup integrity verification failed: hash mismatch. Patch write aborted.",
            )

        backup_record = RepairBackup(
            id=backup_id,
            project_id=project_id,
            proposal_id=proposal_id,
            file_path=clean_path,
            backup_file_path=str(backup_path),
            original_content=original_disk_content,
            original_fingerprint=current_fp,
            status="active",
            created_at=get_utc_now(),
        )
        db.add(backup_record)

        # Transition state: applying
        proposal.repair_status = "applying"
        proposal.apply_attempt_id = str(uuid.uuid4())
        self._record_audit_log(
            db, project_id, proposal_id, "apply_started", clean_path, current_fp,
            {"backup_id": backup_id, "backup_path": str(backup_path)}
        )
        db.commit()

        # 6. Atomic Write to Source File
        temp_file = target_path.with_name(f".tmp_{proposal_id}_{uuid.uuid4().hex[:6]}")
        recovery_attempted = False
        recovery_succeeded = False

        try:
            # Write patched content with original newline conventions to temp file
            newline_char = "\r\n" if "\r\n" in original_disk_content else "\n"
            temp_file.write_text(repaired_source, encoding="utf-8", newline=newline_char)

            # Atomic replace
            os.replace(temp_file, target_path)

            # 7. Post-Application Verification on the Written File
            applied_content = target_path.read_text(encoding="utf-8", errors="replace")
            new_fp = compute_source_fingerprint(applied_content)

            # Concrete Syntax AST Validation on applied content
            self._verify_applied_content(clean_path, applied_content, proposal.language)

        except Exception as apply_err:
            # Failure Recovery: immediately restore backup
            logger.error("Error during patch application or post-write verification: %s. Initiating recovery...", str(apply_err))
            recovery_attempted = True
            try:
                os.replace(backup_path, target_path)
                restored_content = target_path.read_text(encoding="utf-8", errors="replace")
                restored_fp = compute_source_fingerprint(restored_content)
                if restored_fp == current_fp:
                    recovery_succeeded = True
                    backup_record.status = "restored_on_failure"
                    backup_record.restored_at = get_utc_now()
                else:
                    logger.critical("CRITICAL: Restored file fingerprint does not match pre-application fingerprint!")
            except Exception as rec_err:
                logger.critical("CRITICAL RECOVERY FAILURE: Failed to restore backup file: %s", str(rec_err))

            temp_file.unlink(missing_ok=True)

            proposal.repair_status = "failed"
            proposal.apply_error = str(apply_err)
            self._record_audit_log(
                db, project_id, proposal_id, "apply_failed", clean_path, current_fp,
                {
                    "error": str(apply_err),
                    "recovery_attempted": recovery_attempted,
                    "recovery_succeeded": recovery_succeeded,
                    "backup_path": str(backup_path),
                }
            )
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Patch application failed post-write verification: {str(apply_err)}. "
                       f"{'Original source was successfully restored from backup.' if recovery_succeeded else 'CRITICAL: Failed to automatically restore backup. Manual recovery required from ' + str(backup_path)}",
            )

        # 8. Success: Update Proposal and Project File records
        now = get_utc_now()
        proposal.repair_status = "applied"
        proposal.applied_at = now
        proposal.backup_id = backup_id
        proposal.backup_path = str(backup_path)
        proposal.pre_apply_fingerprint = current_fp
        proposal.post_apply_fingerprint = new_fp
        proposal.error_message = None

        # Update ProjectFile DB record size
        file_query = select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.path == clean_path)
        file_rec = db.execute(file_query).scalars().first()
        if file_rec:
            file_rec.size = len(applied_content.encode("utf-8"))
            file_rec.updated_at = now

        self._record_audit_log(
            db, project_id, proposal_id, "applied_successfully", clean_path, new_fp,
            {
                "applied_at": now.isoformat(),
                "backup_id": backup_id,
                "pre_fp": current_fp,
                "post_fp": new_fp,
                "additions": proposal.additions,
                "deletions": proposal.deletions,
            }
        )

        db.commit()
        logger.info("Proposal %s successfully applied to %s (lines +%d, -%d)", proposal_id, clean_path, proposal.additions, proposal.deletions)

        return ApplyRepairResponse(
            proposal_id=proposal_id,
            project_id=project_id,
            file_path=clean_path,
            status="applied",
            applied_at=now.isoformat(),
            backup_id=backup_id,
            backup_path=str(backup_path),
            pre_apply_fingerprint=current_fp,
            post_apply_fingerprint=new_fp,
            syntax_validation_passed=True,
            additions=proposal.additions,
            deletions=proposal.deletions,
            message="Repair patch applied successfully to source file.",
            recovery_attempted=False,
            recovery_succeeded=False,
        )

    # =========================================================================
    # STEP 7: Rollback Engine
    # =========================================================================

    def rollback_patch(
        self, project_id: str, proposal_id: str, db: Session
    ) -> RollbackRepairResponse:
        """
        Reverts an applied patch by restoring the pre-application backup.
        Rejects rollback if user has modified the file since application.
        """
        project, proposal = self._get_proposal_and_verify_project(project_id, proposal_id, db)

        # 1. State check: MUST BE APPLIED
        if proposal.repair_status != "applied":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot rollback proposal in '{proposal.repair_status}' state. Only 'applied' proposals can be rolled back.",
            )

        target_path, clean_path = file_service.sanitize_and_resolve_path(project_id, proposal.file_path)
        if not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target file '{proposal.file_path}' no longer exists on disk.",
            )

        # 2. Check if file has been modified after patch application
        current_disk_content = target_path.read_text(encoding="utf-8", errors="replace")
        current_fp = compute_source_fingerprint(current_disk_content)

        if proposal.post_apply_fingerprint and current_fp != proposal.post_apply_fingerprint:
            self._record_audit_log(
                db, project_id, proposal_id, "rollback_failed", clean_path, current_fp,
                {"reason": "Source file was modified after patch application. Refusing to overwrite newer changes."}
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot rollback repair: the file has been modified since the patch was applied. Overwriting newer changes is prevented.",
            )

        # 3. Retrieve pre-application backup
        backup_query = select(RepairBackup).where(
            RepairBackup.proposal_id == proposal_id,
            RepairBackup.status == "active",
        ).order_by(desc(RepairBackup.created_at))
        backup_record = db.execute(backup_query).scalars().first()

        if not backup_record or not Path(backup_record.backup_file_path).is_file():
            # Fallback check proposal.backup_path
            if proposal.backup_path and Path(proposal.backup_path).is_file():
                backup_path = Path(proposal.backup_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pre-application backup file not found. Safe rollback cannot be guaranteed.",
                )
        else:
            backup_path = Path(backup_record.backup_file_path)

        # Verify backup integrity
        backup_bytes = backup_path.read_bytes()
        backup_content = backup_bytes.decode("utf-8", errors="replace")
        backup_fp = compute_source_fingerprint(backup_content)

        if proposal.pre_apply_fingerprint and backup_fp != proposal.pre_apply_fingerprint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Backup integrity check failed: backup hash does not match original pre-apply hash.",
            )

        # 4. Perform atomic restore
        temp_restore = target_path.with_name(f".rollback_{proposal_id}_{uuid.uuid4().hex[:6]}")
        try:
            temp_restore.write_bytes(backup_bytes)
            os.replace(temp_restore, target_path)
        except Exception as e:
            temp_restore.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Atomic file restore failed during rollback: {str(e)}",
            )

        # 5. Verify restored file
        restored_content = target_path.read_text(encoding="utf-8", errors="replace")
        restored_fp = compute_source_fingerprint(restored_content)

        if proposal.pre_apply_fingerprint and restored_fp != proposal.pre_apply_fingerprint:
            logger.critical("CRITICAL: Restored file does not match expected pre-apply fingerprint!")

        # 6. Update Proposal and Backup records
        now = get_utc_now()
        proposal.repair_status = "rolled_back"
        proposal.rollback_at = now
        proposal.rollback_status = "rolled_back"

        if backup_record:
            backup_record.status = "rolled_back"
            backup_record.restored_at = now

        # Update ProjectFile DB record size
        file_query = select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.path == clean_path)
        file_rec = db.execute(file_query).scalars().first()
        if file_rec:
            file_rec.size = len(backup_bytes)
            file_rec.updated_at = now

        self._record_audit_log(
            db, project_id, proposal_id, "rollback_succeeded", clean_path, restored_fp,
            {"rollback_at": now.isoformat(), "restored_fingerprint": restored_fp}
        )

        db.commit()
        logger.info("Proposal %s successfully rolled back for %s", proposal_id, clean_path)

        return RollbackRepairResponse(
            proposal_id=proposal_id,
            project_id=project_id,
            file_path=clean_path,
            status="rolled_back",
            rollback_at=now.isoformat(),
            restored_fingerprint=restored_fp,
            message="Repair patch successfully rolled back. Original source code restored byte-for-byte.",
        )

    # =========================================================================
    # STEP 8: Audit History API
    # =========================================================================

    def get_audit_history(
        self, project_id: str, proposal_id: str, db: Session
    ) -> ProposalAuditHistoryResponse:
        """
        Returns full immutable audit trail for a repair proposal.
        """
        project, proposal = self._get_proposal_and_verify_project(project_id, proposal_id, db)

        query = select(RepairAuditLog).where(
            RepairAuditLog.proposal_id == proposal_id
        ).order_by(RepairAuditLog.created_at.asc())

        logs = db.execute(query).scalars().all()
        events = []
        for log in logs:
            details = {}
            try:
                details = json.loads(log.details_json or "{}")
            except Exception:
                pass

            events.append(
                AuditLogEntry(
                    id=log.id,
                    proposal_id=log.proposal_id,
                    event_type=log.event_type,
                    target_file=log.target_file,
                    source_fingerprint=log.source_fingerprint,
                    details=details,
                    created_at=log.created_at.isoformat(),
                )
            )

        return ProposalAuditHistoryResponse(
            proposal_id=proposal_id,
            project_id=project_id,
            total_events=len(events),
            events=events,
        )
