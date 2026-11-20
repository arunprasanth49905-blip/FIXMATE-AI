import ast
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import ProjectAnalysis, FileAnalysisRecord
from app.models.detection import DetectionRun, DetectionFinding
from app.models.project import Project, ProjectFile
from app.schemas.detection import (
    DetectionRunResponse,
    DetectionRunSummary,
    Finding,
    FindingSeverity,
    FindingCategory,
    ProjectDetectionRequest,
    SeverityCounts,
)
from app.services.detection.rule_context import RuleContext
from app.services.detection.rule_registry import rule_registry
from app.services.file_service import file_service
from app.services.parsing.parser_limits import ParserLimits
from app.services.parsing.parser_registry import parser_registry

logger = logging.getLogger("fixmate.detection")

ENGINE_VERSION = "1.0.0"


class DetectionEngine:
    """Orchestrates deterministic static bug detection across project workspaces."""

    def __init__(self):
        self.version = ENGINE_VERSION

    def _get_syntax_tree(self, language: str, file_path: str, source_code: str) -> Tuple[Optional[ast.AST], Optional[Any]]:
        """Parses source into Python AST or Tree-sitter Node without executing user code."""
        ast_tree = None
        tree_sitter_node = None

        lang_norm = (language or "").lower()
        if lang_norm in ("python", "py"):
            try:
                ast_tree = ast.parse(source_code, filename=file_path)
            except SyntaxError:
                ast_tree = None
            except Exception as e:
                logger.debug(f"Python parse error on {file_path}: {e}")
                ast_tree = None

        elif lang_norm in ("javascript", "js"):
            try:
                source_bytes = source_code.encode("utf-8")
                js_parser = parser_registry._parsers.get("javascript")
                if js_parser and hasattr(js_parser, "_parser"):
                    tree_sitter_node = js_parser._parser.parse(source_bytes).root_node
            except Exception as e:
                logger.debug(f"JS parse error on {file_path}: {e}")
                tree_sitter_node = None

        elif lang_norm in ("typescript", "ts"):
            try:
                source_bytes = source_code.encode("utf-8")
                ts_parser = parser_registry._parsers.get("typescript")
                if ts_parser and hasattr(ts_parser, "_ts_parser"):
                    p = ts_parser._tsx_parser if file_path.endswith((".tsx", ".jsx")) else ts_parser._ts_parser
                    tree_sitter_node = p.parse(source_bytes).root_node
            except Exception as e:
                logger.debug(f"TS parse error on {file_path}: {e}")
                tree_sitter_node = None

        return ast_tree, tree_sitter_node

    def evaluate_file(
        self,
        file_path: str,
        language: str,
        source_code: str,
        rule_ids: Optional[List[str]] = None,
        file_analysis: Optional[Any] = None,
    ) -> List[Finding]:
        """Evaluates a single file against registered detection rules."""
        rules = rule_registry.get_rules_for_language(language)
        if rule_ids:
            rules = [r for r in rules if r.rule_id in rule_ids]

        if not rules:
            return []

        ast_tree, tree_sitter_node = self._get_syntax_tree(language, file_path, source_code)

        context = RuleContext(
            file_path=file_path,
            language=language,
            source_code=source_code,
            ast_tree=ast_tree,
            tree_sitter_node=tree_sitter_node,
            file_analysis=file_analysis,
        )

        all_findings: List[Finding] = []
        for rule in rules:
            try:
                findings = rule.evaluate(context)
                all_findings.extend(findings)
            except Exception as exc:
                logger.warning(f"Rule {rule.rule_id} failed on {file_path}: {exc}", exc_info=True)

        return all_findings

    def run_project_detection(
        self,
        db: Session,
        project_id: str,
        request: Optional[ProjectDetectionRequest] = None,
    ) -> DetectionRunResponse:
        """Executes full or filtered bug detection across the project workspace."""
        start_time = time.perf_counter()
        run_id = str(uuid.uuid4())

        project = db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        workspace_dir = settings.get_workspace_dir(project_id).resolve()
        if not workspace_dir.exists():
            raise ValueError(f"Project workspace directory does not exist: {workspace_dir}")

        # Check for Phase 3 analysis to link
        analysis_id = None
        if request is None or request.reuse_analysis:
            latest_analysis = (
                db.query(ProjectAnalysis)
                .filter(ProjectAnalysis.project_id == project_id)
                .order_by(desc(ProjectAnalysis.start_time))
                .first()
            )
            if latest_analysis:
                analysis_id = latest_analysis.id

        warnings: List[str] = []
        target_rule_ids = request.rule_ids if request else None
        target_severities = set(request.severities) if request and request.severities else None

        # Discover candidate files in workspace
        candidate_paths: List[Tuple[Path, str]] = []
        for path_obj in workspace_dir.rglob("*"):
            if not path_obj.is_file():
                continue
            rel_path = path_obj.relative_to(workspace_dir).as_posix()
            is_excluded, _ = ParserLimits.is_excluded_path(rel_path)
            if is_excluded:
                continue
            if not parser_registry.is_supported_path(rel_path):
                continue
            if request and request.file_paths and rel_path not in request.file_paths:
                continue
            candidate_paths.append((path_obj, rel_path))

        # Enforce file limits
        if len(candidate_paths) > settings.MAX_FILES_PER_ANALYSIS:
            warnings.append(
                f"Project exceeds max file limit ({len(candidate_paths)} > {settings.MAX_FILES_PER_ANALYSIS}). "
                f"Analyzing first {settings.MAX_FILES_PER_ANALYSIS} files."
            )
            candidate_paths = candidate_paths[:settings.MAX_FILES_PER_ANALYSIS]

        total_bytes = 0
        scanned_count = 0
        all_findings: List[Finding] = []

        for p, rel_path in candidate_paths:

            try:
                stat = p.stat()
                if stat.st_size > settings.MAX_PARSER_FILE_SIZE_BYTES:
                    warnings.append(f"Skipped {rel_path}: file size {stat.st_size} exceeds 1MB limit.")
                    continue

                if total_bytes + stat.st_size > settings.MAX_TOTAL_ANALYSIS_SOURCE_BYTES:
                    warnings.append(f"Analysis ceiling reached (25MB limit). Stopped scanning additional files.")
                    break

                total_bytes += stat.st_size

                with open(p, "r", encoding="utf-8", errors="replace") as f_obj:
                    source_code = f_obj.read()

                parser = parser_registry.get_parser_for_path(str(p))
                lang = parser.language if parser else "Unknown"

                # Find any pre-computed Phase 3 file analysis record
                file_analysis_record = None
                if analysis_id:
                    file_analysis_record = (
                        db.query(FileAnalysisRecord)
                        .filter(
                            FileAnalysisRecord.analysis_id == analysis_id,
                            FileAnalysisRecord.file_path == rel_path,
                        )
                        .first()
                    )

                findings = self.evaluate_file(
                    file_path=rel_path,
                    language=lang,
                    source_code=source_code,
                    rule_ids=target_rule_ids,
                    file_analysis=file_analysis_record,
                )

                for finding in findings:
                    finding.run_id = run_id
                    finding.project_id = project_id
                    if not target_severities or finding.severity in target_severities:
                        all_findings.append(finding)

                scanned_count += 1

            except Exception as e:
                logger.warning(f"Error scanning file {rel_path}: {e}")
                warnings.append(f"Error evaluating {rel_path}: {str(e)}")

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Calculate counts
        severity_counts = SeverityCounts()
        category_counts: Dict[str, int] = {}
        for f in all_findings:
            if f.severity == FindingSeverity.CRITICAL:
                severity_counts.critical += 1
            elif f.severity == FindingSeverity.HIGH:
                severity_counts.high += 1
            elif f.severity == FindingSeverity.MEDIUM:
                severity_counts.medium += 1
            elif f.severity == FindingSeverity.LOW:
                severity_counts.low += 1
            elif f.severity == FindingSeverity.INFO:
                severity_counts.info += 1

            cat_str = f.category.value if hasattr(f.category, "value") else str(f.category)
            category_counts[cat_str] = category_counts.get(cat_str, 0) + 1

        run_status = "completed_with_findings" if all_findings else "completed"

        # Persist to SQLite
        db_run = DetectionRun(
            id=run_id,
            project_id=project_id,
            analysis_id=analysis_id,
            status=run_status,
            engine_version=self.version,
            created_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            files_scanned=scanned_count,
            total_findings=len(all_findings),
            critical_count=severity_counts.critical,
            high_count=severity_counts.high,
            medium_count=severity_counts.medium,
            low_count=severity_counts.low,
            info_count=severity_counts.info,
            findings_by_severity_json=json.dumps(severity_counts.model_dump()),
            findings_by_category_json=json.dumps(category_counts),
            warnings_json=json.dumps(warnings),
        )
        db.add(db_run)

        # Batch insert findings
        for f in all_findings:
            db_finding = DetectionFinding(
                id=f.id,
                run_id=run_id,
                project_id=project_id,
                rule_id=f.rule_id,
                rule_name=f.rule_name,
                language=f.language,
                severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                confidence=f.confidence,
                category=f.category.value if hasattr(f.category, "value") else str(f.category),
                file_path=f.file_path,
                start_line=f.start_line,
                start_column=f.start_column,
                end_line=f.end_line,
                end_column=f.end_column,
                message=f.message,
                explanation=f.explanation,
                evidence=f.evidence,
                remediation=f.remediation,
            )
            db.add(db_finding)

        db.commit()

        return DetectionRunResponse(
            run_id=run_id,
            project_id=project_id,
            analysis_id=analysis_id,
            status=run_status,
            engine_version=self.version,
            created_at=db_run.created_at.isoformat(),
            duration_ms=duration_ms,
            files_scanned=scanned_count,
            total_findings=len(all_findings),
            severity_counts=severity_counts,
            findings_by_category=category_counts,
            warnings=warnings,
            findings=all_findings,
        )

    def get_latest_run(self, db: Session, project_id: str) -> Optional[DetectionRunResponse]:
        """Retrieves the latest detection run and its findings."""
        db_run = (
            db.query(DetectionRun)
            .filter(DetectionRun.project_id == project_id)
            .order_by(desc(DetectionRun.created_at))
            .first()
        )
        if not db_run:
            return None
        return self._format_run_response(db, db_run)

    def get_run_by_id(self, db: Session, project_id: str, run_id: str) -> Optional[DetectionRunResponse]:
        """Retrieves a specific historical detection run."""
        db_run = (
            db.query(DetectionRun)
            .filter(DetectionRun.id == run_id, DetectionRun.project_id == project_id)
            .first()
        )
        if not db_run:
            return None
        return self._format_run_response(db, db_run)

    def _format_run_response(self, db: Session, db_run: DetectionRun) -> DetectionRunResponse:
        db_findings = (
            db.query(DetectionFinding)
            .filter(DetectionFinding.run_id == db_run.id)
            .order_by(DetectionFinding.file_path, DetectionFinding.start_line)
            .all()
        )

        findings = [
            Finding(
                id=df.id,
                run_id=df.run_id,
                project_id=df.project_id,
                rule_id=df.rule_id,
                rule_name=df.rule_name,
                language=df.language,
                severity=FindingSeverity(df.severity),
                confidence=df.confidence,
                category=FindingCategory(df.category),
                file_path=df.file_path,
                start_line=df.start_line,
                start_column=df.start_column,
                end_line=df.end_line,
                end_column=df.end_column,
                message=df.message,
                explanation=df.explanation,
                evidence=df.evidence,
                remediation=df.remediation,
            )
            for df in db_findings
        ]

        try:
            sev_data = json.loads(db_run.findings_by_severity_json)
            severity_counts = SeverityCounts(**sev_data)
        except Exception:
            severity_counts = SeverityCounts(
                critical=db_run.critical_count,
                high=db_run.high_count,
                medium=db_run.medium_count,
                low=db_run.low_count,
                info=db_run.info_count,
            )

        try:
            cat_data = json.loads(db_run.findings_by_category_json)
        except Exception:
            cat_data = {}

        try:
            warn_data = json.loads(db_run.warnings_json)
        except Exception:
            warn_data = []

        return DetectionRunResponse(
            run_id=db_run.id,
            project_id=db_run.project_id,
            analysis_id=db_run.analysis_id,
            status=db_run.status,
            engine_version=db_run.engine_version,
            created_at=db_run.created_at.isoformat(),
            duration_ms=db_run.duration_ms,
            files_scanned=db_run.files_scanned,
            total_findings=db_run.total_findings,
            severity_counts=severity_counts,
            findings_by_category=cat_data,
            warnings=warn_data,
            findings=findings,
        )


detection_engine = DetectionEngine()
