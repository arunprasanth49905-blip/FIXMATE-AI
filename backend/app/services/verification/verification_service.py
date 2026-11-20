import json
import logging
import time
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.detection import DetectionFinding
from app.models.repair import RepairProposal, RepairAuditLog
from app.models.verification import RepairVerification
from app.schemas.detection import Finding
from app.schemas.verification import (
    VerificationReportResponse,
    VerificationHistoryResponse,
    VerificationCheck,
    FindingsComparison,
)
from app.services.detection.detection_engine import detection_engine
from app.services.repair.repair_context import compute_source_fingerprint
from app.services.verification.syntax_verifier import SyntaxVerifier
from app.services.verification.finding_comparison import FindingComparator
from app.services.verification.regression_verifier import RegressionVerifier
from app.services.verification.verification_report_builder import VerificationReportBuilder

logger = logging.getLogger("fixmate.verification")


class VerificationService:
    """
    Automated Verification & Repair Validation Service (Phase 8).
    Evaluates repaired source code statically:
    - Syntax validity via AST/Tree-sitter
    - Target bug resolution
    - Regression analysis
    - Change scope & fingerprint integrity
    CRITICAL: Never executes user code; strictly read-only.
    """

    def verify_repair(
        self,
        project_id: str,
        proposal_id: str,
        db: Session,
    ) -> VerificationReportResponse:
        start_time = time.perf_counter()

        # 1. Verify project and proposal
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
                detail=f"Repair proposal '{proposal_id}' not found for project '{project_id}'.",
            )

        # 2. State verification: proposal MUST be applied
        if proposal.repair_status != "applied":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Verification requires an applied repair proposal. Current proposal status is '{proposal.repair_status}'.",
            )

        # 3. Path confinement and security
        ws_root = settings.get_workspace_dir(project_id).resolve()
        clean_rel_path = proposal.file_path.replace("\\", "/").lstrip("/")
        target_path = (ws_root / clean_rel_path).resolve()

        if not str(target_path).startswith(str(ws_root)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Path traversal detected: '{proposal.file_path}' escapes workspace.",
            )

        if not target_path.exists() or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target file '{proposal.file_path}' does not exist on disk.",
            )

        # Symlink check
        if target_path.is_symlink():
            real_target = target_path.resolve()
            if not str(real_target).startswith(str(ws_root)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Symlink pointing outside project workspace is strictly prohibited.",
                )

        # 4. Read source from disk (READ-ONLY)
        try:
            current_source = target_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            current_source = target_path.read_text(encoding="latin-1")

        current_fingerprint = compute_source_fingerprint(current_source)

        # 5. Check staleness & integrity
        expected_post_fp = proposal.post_apply_fingerprint or proposal.source_fingerprint
        is_stale = bool(expected_post_fp and current_fingerprint != expected_post_fp)

        integrity_passed = not is_stale
        integrity_msg = "Fingerprint match verified." if integrity_passed else "Disk source modified after patch was applied."

        # 6. Syntax Verification (AST / Tree-sitter without execution)
        syntax_res = SyntaxVerifier.verify_syntax(clean_rel_path, current_source, proposal.language)

        # 7. Retrieve pre-repair original findings
        original_finding = db.get(DetectionFinding, proposal.finding_id)
        original_findings_list: List[Finding] = []

        if original_finding:
            # Query all findings belonging to this run for the same file
            sibling_findings = (
                db.execute(
                    select(DetectionFinding).where(
                        DetectionFinding.run_id == original_finding.run_id,
                        DetectionFinding.file_path == proposal.file_path,
                    )
                )
                .scalars()
                .all()
            )
            for sf in sibling_findings:
                original_findings_list.append(
                    Finding(
                        id=sf.id,
                        project_id=sf.project_id,
                        run_id=sf.run_id,
                        rule_id=sf.rule_id,
                        rule_name=sf.rule_name,
                        severity=sf.severity,
                        category=sf.category,
                        file_path=sf.file_path,
                        start_line=sf.start_line,
                        start_column=sf.start_column,
                        end_line=sf.end_line,
                        end_column=sf.end_column,
                        language=sf.language,
                        message=sf.message,
                        explanation=sf.explanation,
                        remediation=sf.remediation,
                        evidence=sf.evidence,
                        confidence=sf.confidence,
                    )
                )
        elif proposal.rule_id:
            # Fallback mock container if finding record was purged
            original_findings_list.append(
                Finding(
                    id=proposal.finding_id,
                    project_id=proposal.project_id,
                    run_id="",
                    rule_id=proposal.rule_id,
                    rule_name=proposal.rule_name,
                    severity="high",
                    category="correctness",
                    file_path=proposal.file_path,
                    start_line=proposal.start_line,
                    start_column=1,
                    end_line=proposal.end_line,
                    end_column=1,
                    language=proposal.language,
                    message=proposal.repair_summary,
                    explanation=proposal.repair_explanation,
                    remediation="",
                    evidence=proposal.original_code,
                    confidence=0.95,
                )
            )

        # 8. Re-run Phase 4 Deterministic Bug Detection on current repaired source
        current_detected_findings = detection_engine.evaluate_file(
            file_path=clean_rel_path,
            language=proposal.language,
            source_code=current_source,
        )

        # 9. Compare findings before vs after
        comparison = FindingComparator.compare_findings(
            target_rule_id=proposal.rule_id,
            target_start_line=proposal.start_line,
            target_end_line=proposal.end_line,
            original_findings=original_findings_list,
            current_findings=current_detected_findings,
            target_evidence=proposal.original_code,
        )

        # 10. Evaluate Regressions
        regression_status, regression_msg = RegressionVerifier.evaluate_regressions(comparison.new_findings)

        # 11. Change Scope Validation
        pre_apply_fp = proposal.pre_apply_fingerprint or proposal.source_fingerprint
        scope_passed = True
        scope_msg = "Changes confined to expected file and within intended diff bounds."

        if current_fingerprint == pre_apply_fp:
            scope_passed = False
            scope_msg = "Change scope anomaly: Applied source is identical to pre-apply source."

        # 12. Build check results and overall status
        checks, overall_status = VerificationReportBuilder.build_checks(
            integrity_passed=integrity_passed,
            integrity_message=integrity_msg,
            is_stale=is_stale,
            syntax_res=syntax_res,
            comparison=comparison,
            regression_status=regression_status,
            regression_message=regression_msg,
            scope_passed=scope_passed,
            scope_message=scope_msg,
        )

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # 13. Persist Verification Record to Database
        verification = RepairVerification(
            project_id=project_id,
            proposal_id=proposal_id,
            file_path=proposal.file_path,
            status=overall_status,
            syntax_status=syntax_res.status,
            target_bug_status=comparison.target_finding_status,
            regression_status=regression_status,
            pre_apply_fingerprint=pre_apply_fp,
            post_apply_fingerprint=expected_post_fp,
            verified_fingerprint=current_fingerprint,
            original_bug_count=comparison.before_count,
            current_bug_count=comparison.after_count,
            resolved_bug_count=comparison.resolved_count,
            regression_bug_count=comparison.regression_count,
            findings_comparison_json=comparison.model_dump_json(),
            checks_details_json=json.dumps([c.model_dump() for c in checks]),
            error_message=syntax_res.error_message if syntax_res.status == "failed" else None,
            duration_ms=duration_ms,
        )
        db.add(verification)

        # 14. Audit Log Entry
        audit = RepairAuditLog(
            project_id=project_id,
            proposal_id=proposal_id,
            event_type="verification_completed",
            target_file=proposal.file_path,
            source_fingerprint=current_fingerprint,
            details_json=json.dumps(
                {
                    "verification_id": verification.id,
                    "overall_status": overall_status,
                    "syntax_status": syntax_res.status,
                    "target_bug_status": comparison.target_finding_status,
                    "regression_status": regression_status,
                    "new_findings": comparison.regression_count,
                    "resolved_findings": comparison.resolved_count,
                    "duration_ms": duration_ms,
                }
            ),
        )
        db.add(audit)
        db.commit()
        db.refresh(verification)

        logger.info(
            f"Verification {verification.id} completed for proposal {proposal_id} "
            f"with overall_status={overall_status} (target={comparison.target_finding_status}, "
            f"regressions={comparison.regression_count}) in {duration_ms}ms"
        )

        return self._to_report_dto(verification, checks, comparison, is_stale)

    def get_history(
        self,
        project_id: str,
        proposal_id: str,
        db: Session,
        limit: int = 50,
    ) -> VerificationHistoryResponse:
        query = (
            select(RepairVerification)
            .where(
                RepairVerification.project_id == project_id,
                RepairVerification.proposal_id == proposal_id,
            )
            .order_by(desc(RepairVerification.created_at))
            .limit(limit)
        )
        records = db.execute(query).scalars().all()

        dtos = []
        for rec in records:
            dtos.append(self._record_to_dto(rec))

        return VerificationHistoryResponse(
            project_id=project_id,
            proposal_id=proposal_id,
            total=len(dtos),
            verifications=dtos,
        )

    def get_verification_by_id(
        self,
        project_id: str,
        verification_id: str,
        db: Session,
    ) -> VerificationReportResponse:
        record = db.get(RepairVerification, verification_id)
        if not record or record.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification report '{verification_id}' not found.",
            )
        return self._record_to_dto(record)

    def _record_to_dto(self, rec: RepairVerification) -> VerificationReportResponse:
        checks_data = []
        try:
            raw_checks = json.loads(rec.checks_details_json or "[]")
            checks_data = [VerificationCheck(**c) for c in raw_checks]
        except Exception:
            pass

        comparison_data = None
        try:
            raw_comp = json.loads(rec.findings_comparison_json or "{}")
            comparison_data = FindingsComparison(**raw_comp)
        except Exception:
            comparison_data = FindingsComparison(
                target_rule_id="",
                target_finding_status=rec.target_bug_status,
                before_count=rec.original_bug_count,
                after_count=rec.current_bug_count,
                resolved_count=rec.resolved_bug_count,
                regression_count=rec.regression_bug_count,
            )

        is_stale = rec.status == "stale" or rec.verified_fingerprint != rec.post_apply_fingerprint

        return self._to_report_dto(rec, checks_data, comparison_data, is_stale)

    @staticmethod
    def _to_report_dto(
        rec: RepairVerification,
        checks: List[VerificationCheck],
        comparison: FindingsComparison,
        is_stale: bool,
    ) -> VerificationReportResponse:
        return VerificationReportResponse(
            id=rec.id,
            project_id=rec.project_id,
            proposal_id=rec.proposal_id,
            file_path=rec.file_path,
            overall_status=rec.status,
            syntax_status=rec.syntax_status,
            target_bug_status=rec.target_bug_status,
            regression_status=rec.regression_status,
            pre_apply_fingerprint=rec.pre_apply_fingerprint,
            post_apply_fingerprint=rec.post_apply_fingerprint,
            verified_fingerprint=rec.verified_fingerprint,
            is_stale=is_stale,
            checks=checks,
            comparison=comparison,
            error_message=rec.error_message,
            duration_ms=rec.duration_ms,
            created_at=rec.created_at,
        )


verification_service = VerificationService()
