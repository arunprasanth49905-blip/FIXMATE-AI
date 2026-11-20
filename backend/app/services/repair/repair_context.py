import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.models.detection import DetectionFinding
from app.models.root_cause import RootCauseAnalysis
from app.services.file_service import FileService
from app.services.root_cause.root_cause_context import redact_sensitive_data

file_service = FileService()


def compute_source_fingerprint(source_code: str) -> str:
    """Computes a SHA-256 fingerprint of the source text with normalized newlines."""
    normalized = source_code.replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class RepairContext:
    project_id: str
    finding_id: str
    rca_id: Optional[str]
    rule_id: str
    rule_name: str
    language: str
    file_path: str
    start_line: int
    end_line: int
    severity: str

    # Phase 4 Finding Context
    finding_message: str
    finding_explanation: str
    finding_evidence: str
    finding_remediation: str

    # Phase 5 RCA Context
    rca_summary: str
    rca_simple_explanation: str
    rca_root_cause: str
    rca_suggested_code: str
    rca_explanation: str
    rca_assumptions: List[str] = field(default_factory=list)

    # Source Integrity
    source_fingerprint: str = ""
    full_source_raw: str = ""
    exact_original_code: str = ""
    padded_context_snippet: str = ""
    is_stale: bool = False
    staleness_reason: Optional[str] = None


class RepairContextBuilder:
    MAX_SNIPPET_CHARS = 8000
    DEFAULT_PADDING = 15

    @classmethod
    def build_context(
        cls,
        project_id: str,
        finding_id: str,
        db: Session,
        padding: int = DEFAULT_PADDING,
    ) -> RepairContext:
        """
        Gathers finding, latest RCA, and current disk source code.
        Computes source fingerprint and verifies that the source hasn't gone stale.
        """
        # 1. Fetch Finding
        finding = db.get(DetectionFinding, finding_id)
        if not finding or finding.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection finding '{finding_id}' not found in project '{project_id}'.",
            )

        # 2. Fetch Latest Root Cause Analysis for Finding
        rca_query = (
            select(RootCauseAnalysis)
            .where(
                RootCauseAnalysis.project_id == project_id,
                RootCauseAnalysis.finding_id == finding_id,
            )
            .order_by(desc(RootCauseAnalysis.created_at))
        )
        rca = db.execute(rca_query).scalars().first()
        if not rca:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Finding '{finding_id}' requires a completed Root Cause Analysis before repair generation.",
            )

        # 3. Read current file on disk
        target_path, clean_rel = file_service.sanitize_and_resolve_path(project_id, finding.file_path)
        if not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source file '{finding.file_path}' not found in workspace.",
            )

        raw_code = target_path.read_text(encoding="utf-8", errors="replace")
        fingerprint = compute_source_fingerprint(raw_code)
        lines = raw_code.splitlines()
        total_lines = len(lines)

        # 4. Check for Source Staleness
        is_stale = False
        staleness_reason = None

        if total_lines == 0:
            is_stale = True
            staleness_reason = "Source file on disk is empty."
        elif finding.start_line < 1 or finding.start_line > total_lines:
            is_stale = True
            staleness_reason = f"Error line {finding.start_line} is out of bounds for current file ({total_lines} lines)."
        else:
            # Check if line content still resembles the finding's evidence
            to_line = min(total_lines, max(finding.start_line, finding.end_line))
            target_slice = lines[finding.start_line - 1 : to_line]
            current_target = "\n".join(target_slice).strip()
            evidence_clean = finding.evidence.strip() if finding.evidence else ""

            # If evidence was provided and does not match at all
            if evidence_clean and evidence_clean not in current_target and current_target not in evidence_clean:
                # Fuzzy check: check if evidence exists anywhere in file
                if evidence_clean not in raw_code:
                    is_stale = True
                    staleness_reason = f"Source code at line {finding.start_line} has changed since detection."

        # 5. Extract exact original target code
        exact_code = ""
        if not is_stale and total_lines > 0:
            to_line = min(total_lines, max(finding.start_line, finding.end_line))
            exact_code = "\n".join(lines[finding.start_line - 1 : to_line])
        elif finding.evidence:
            exact_code = finding.evidence

        # 6. Format padded context snippet
        from_line = max(1, finding.start_line - padding)
        to_line = min(total_lines, finding.end_line + padding)
        formatted_lines = []
        for line_idx in range(from_line, to_line + 1):
            if line_idx <= total_lines:
                actual_line = lines[line_idx - 1]
                is_finding_line = finding.start_line <= line_idx <= finding.end_line
                marker = ">>>" if is_finding_line else "   "
                formatted_lines.append(f"{marker} {line_idx:4d} | {actual_line}")

        snippet = "\n".join(formatted_lines)
        safe_snippet = redact_sensitive_data(snippet)
        if len(safe_snippet) > cls.MAX_SNIPPET_CHARS:
            safe_snippet = safe_snippet[: cls.MAX_SNIPPET_CHARS] + "\n... [Context truncated for length] ..."

        # 7. Unpack RCA fields
        import json
        assumptions = []
        try:
            assumptions = json.loads(rca.assumptions_json or "[]")
        except Exception:
            pass

        return RepairContext(
            project_id=project_id,
            finding_id=finding_id,
            rca_id=rca.id,
            rule_id=finding.rule_id,
            rule_name=finding.rule_name,
            language=finding.language,
            file_path=finding.file_path,
            start_line=finding.start_line,
            end_line=finding.end_line,
            severity=finding.severity,
            finding_message=finding.message,
            finding_explanation=finding.explanation,
            finding_evidence=finding.evidence,
            finding_remediation=finding.remediation,
            rca_summary=rca.summary,
            rca_simple_explanation=rca.simple_explanation,
            rca_root_cause=rca.root_cause,
            rca_suggested_code=rca.corrected_code,
            rca_explanation=rca.correction_explanation,
            rca_assumptions=assumptions,
            source_fingerprint=fingerprint,
            full_source_raw=raw_code,
            exact_original_code=redact_sensitive_data(exact_code),
            padded_context_snippet=safe_snippet,
            is_stale=is_stale,
            staleness_reason=staleness_reason,
        )
