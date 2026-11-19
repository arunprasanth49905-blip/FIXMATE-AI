import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.config import settings
from app.core.logging import logger
from app.models.project import Project, ProjectFile
from app.models.analysis import ProjectAnalysis, FileAnalysisRecord
from app.schemas.parsing import (
    ProjectAnalysisResponse,
    ProjectAnalysisSummary,
    ProjectStatistics,
    FileAnalysis,
    SkippedFile,
    SyntaxDiagnostic,
    ProjectParseRequest,
)
from app.services.parsing.parser_limits import ParserLimits
from app.services.parsing.parser_registry import parser_registry
from app.services.parsing.syntax_diagnostics import DiagnosticsFactory


class ProjectAnalysisService:
    def parse_project(
        self,
        db: Session,
        project_id: str,
        request: Optional[ProjectParseRequest] = None,
    ) -> ProjectAnalysisResponse:
        """Executes full static parsing and structural analysis on a project's workspace."""
        start_time_dt = datetime.now(timezone.utc)
        start_perf = time.perf_counter()

        # 1. Verify project exists
        project = db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        workspace_dir = settings.get_workspace_dir(project_id)
        analysis_id = str(uuid.uuid4())

        # 2. File discovery
        discovered_files: List[Tuple[Path, str]] = []  # (absolute_path, relative_path)
        all_file_count = 0
        total_source_bytes = 0
        skipped_files: List[SkippedFile] = []
        warnings: List[str] = []

        custom_excludes = request.exclude_dirs if request else None

        # Build a lookup of existing DB files by normalized path
        existing_db_files = {f.path: f for f in project.files if not f.is_directory}

        for path_obj in workspace_dir.rglob("*"):
            if not path_obj.is_file():
                continue

            all_file_count += 1
            rel_path = path_obj.relative_to(workspace_dir).as_posix()

            # Check directory exclusions & sensitive files
            is_excluded, reason = ParserLimits.is_excluded_path(rel_path, custom_excludes)
            if is_excluded:
                continue

            # Check supported extensions
            if not parser_registry.is_supported_path(rel_path):
                continue

            # Filter if specific file_ids or file_paths were requested
            if request:
                if request.file_paths and rel_path not in request.file_paths:
                    continue
                if request.file_ids:
                    db_file = existing_db_files.get(rel_path)
                    if not db_file or db_file.id not in request.file_ids:
                        continue

            file_size = path_obj.stat().st_size

            # Single file size check
            size_valid, size_reason = ParserLimits.validate_file_size(file_size)
            if not size_valid:
                skipped_files.append(SkippedFile(file_path=rel_path, reason=size_reason, size_bytes=file_size))
                warnings.append(f"Skipped {rel_path}: {size_reason}")
                continue

            total_source_bytes += file_size
            discovered_files.append((path_obj, rel_path))

        # Check project-wide limits
        limit_valid, limit_reason = ParserLimits.validate_project_limits(len(discovered_files), total_source_bytes)
        if not limit_valid:
            warnings.append(f"Resource limit warning: {limit_reason}")
            # Truncate to maximum allowable files if exceeded
            if len(discovered_files) > settings.MAX_FILES_PER_ANALYSIS:
                discovered_files = discovered_files[:settings.MAX_FILES_PER_ANALYSIS]

        # 3. Parse discovered files
        analyzed_files: List[FileAnalysis] = []
        lang_distribution: Dict[str, int] = {}
        project_stats = ProjectStatistics(
            total_files=all_file_count,
            supported_files=len(discovered_files),
        )

        for abs_path, rel_path in discovered_files:
            parser = parser_registry.get_parser_for_path(rel_path)
            if not parser:
                continue

            db_file = existing_db_files.get(rel_path)
            file_id = db_file.id if db_file else None

            try:
                source_code = abs_path.read_text(encoding="utf-8", errors="replace")
                analysis = parser.parse(
                    source_code=source_code,
                    file_path=rel_path,
                    file_id=file_id,
                    project_id=project_id,
                    analysis_id=analysis_id,
                )
            except Exception as parse_err:
                logger.error(f"Error parsing file {rel_path}: {parse_err}")
                diag = DiagnosticsFactory.create(
                    file_path=rel_path,
                    file_id=file_id,
                    message=f"File read or parse exception: {str(parse_err)}",
                    line=1,
                    severity="error",
                    parser_name=parser.parser_name,
                )
                analysis = FileAnalysis(
                    analysis_id=analysis_id,
                    project_id=project_id,
                    file_id=file_id,
                    file_path=rel_path,
                    language=parser.language,
                    parser=parser.parser_name,
                    status="failed",
                    source_hash="",
                    source_size=0,
                    analysis_timestamp=datetime.now(timezone.utc).isoformat(),
                    statistics=project_stats.__class__(),
                    symbols=[],
                    imports=[],
                    diagnostics=[diag],
                )

            analyzed_files.append(analysis)

            # Update language distribution
            lang = analysis.language
            lang_distribution[lang] = lang_distribution.get(lang, 0) + 1
            if lang == "Python":
                project_stats.python_files += 1
            elif lang == "JavaScript":
                project_stats.javascript_files += 1
            elif lang == "TypeScript":
                project_stats.typescript_files += 1

            # Update status counts
            if analysis.status == "success":
                project_stats.parsed_files += 1
            elif analysis.status == "diagnostics":
                project_stats.parsed_files += 1
            elif analysis.status == "failed":
                project_stats.failed_files += 1
            elif analysis.status == "skipped":
                project_stats.skipped_files += 1

            # Aggregate stats
            s = analysis.statistics
            project_stats.total_lines += s.lines
            project_stats.total_functions += s.functions
            project_stats.total_async_functions += s.async_functions
            project_stats.total_classes += s.classes
            project_stats.total_methods += s.methods
            project_stats.total_imports += s.imports
            project_stats.total_variables += (s.variables + s.constants)
            project_stats.total_loops += s.loops
            project_stats.total_conditions += s.conditions
            project_stats.total_calls += s.calls
            project_stats.total_diagnostics += len(analysis.diagnostics)

        project_stats.skipped_files += len(skipped_files)

        end_time_dt = datetime.now(timezone.utc)
        duration_ms = round((time.perf_counter() - start_perf) * 1000, 2)
        project_stats.duration_ms = duration_ms

        # Determine overall project analysis status
        if project_stats.failed_files > 0 and project_stats.parsed_files == 0:
            overall_status = "failed"
        elif project_stats.total_diagnostics > 0:
            overall_status = "completed_with_diagnostics"
        else:
            overall_status = "completed"

        # 4. Persist to Database
        summary_dict = {
            "language_distribution": lang_distribution,
            "skipped_files": [sf.model_dump() for sf in skipped_files],
            "warnings": warnings,
            "total_diagnostics_count": project_stats.total_diagnostics,
        }

        analysis_record = ProjectAnalysis(
            id=analysis_id,
            project_id=project_id,
            status=overall_status,
            start_time=start_time_dt,
            end_time=end_time_dt,
            duration_ms=duration_ms,
            total_files=project_stats.total_files,
            parsed_files=project_stats.parsed_files,
            failed_files=project_stats.failed_files,
            skipped_files=project_stats.skipped_files,
            statistics_json=json.dumps(project_stats.model_dump()),
            summary_json=json.dumps(summary_dict),
        )
        db.add(analysis_record)

        # Add file records
        for fa in analyzed_files:
            file_rec = FileAnalysisRecord(
                id=str(uuid.uuid4()),
                analysis_id=analysis_id,
                file_id=fa.file_id,
                file_path=fa.file_path,
                language=fa.language,
                parser_name=fa.parser,
                status=fa.status,
                source_hash=fa.source_hash,
                source_size=fa.source_size,
                statistics_json=json.dumps(fa.statistics.model_dump()),
                symbols_json=json.dumps([s.model_dump() for s in fa.symbols]),
                imports_json=json.dumps([imp.model_dump() for imp in fa.imports]),
                diagnostics_json=json.dumps([d.model_dump() for d in fa.diagnostics]),
                structure_json=json.dumps(fa.structure),
            )
            db.add(file_rec)

        db.commit()

        return ProjectAnalysisResponse(
            analysis_id=analysis_id,
            project_id=project_id,
            status=overall_status,
            start_time=start_time_dt.isoformat(),
            end_time=end_time_dt.isoformat(),
            duration_ms=duration_ms,
            statistics=project_stats,
            language_distribution=lang_distribution,
            skipped_files=skipped_files,
            warnings=warnings,
            total_diagnostics_count=project_stats.total_diagnostics,
            files=analyzed_files,
        )

    def get_latest_analysis(self, db: Session, project_id: str) -> Optional[ProjectAnalysisResponse]:
        """Retrieves the most recent analysis for a given project."""
        stmt = (
            select(ProjectAnalysis)
            .where(ProjectAnalysis.project_id == project_id)
            .order_by(desc(ProjectAnalysis.created_at))
            .limit(1)
        )
        record = db.execute(stmt).scalars().first()
        if not record:
            return None
        return self._build_analysis_response(record)

    def get_analysis_by_id(self, db: Session, project_id: str, analysis_id: str) -> Optional[ProjectAnalysisResponse]:
        """Retrieves an analysis record by its ID."""
        stmt = (
            select(ProjectAnalysis)
            .where(ProjectAnalysis.id == analysis_id, ProjectAnalysis.project_id == project_id)
        )
        record = db.execute(stmt).scalars().first()
        if not record:
            return None
        return self._build_analysis_response(record)

    def _build_analysis_response(self, record: ProjectAnalysis) -> ProjectAnalysisResponse:
        stats_dict = json.loads(record.statistics_json) if record.statistics_json else {}
        summary_dict = json.loads(record.summary_json) if record.summary_json else {}

        stats = ProjectStatistics(**stats_dict)
        skipped = [SkippedFile(**sf) for sf in summary_dict.get("skipped_files", [])]

        files_list: List[FileAnalysis] = []
        for fr in record.file_records:
            f_stats = json.loads(fr.statistics_json) if fr.statistics_json else {}
            f_syms = json.loads(fr.symbols_json) if fr.symbols_json else []
            f_imps = json.loads(fr.imports_json) if fr.imports_json else []
            f_diag = json.loads(fr.diagnostics_json) if fr.diagnostics_json else []
            f_struct = json.loads(fr.structure_json) if fr.structure_json else {}

            files_list.append(
                FileAnalysis(
                    analysis_id=record.id,
                    project_id=record.project_id,
                    file_id=fr.file_id,
                    file_path=fr.file_path,
                    language=fr.language,
                    parser=fr.parser_name,
                    status=fr.status,
                    source_hash=fr.source_hash,
                    source_size=fr.source_size,
                    analysis_timestamp=fr.created_at.isoformat(),
                    statistics=f_stats,
                    symbols=f_syms,
                    imports=f_imps,
                    diagnostics=f_diag,
                    structure=f_struct,
                )
            )

        return ProjectAnalysisResponse(
            analysis_id=record.id,
            project_id=record.project_id,
            status=record.status,
            start_time=record.start_time.isoformat(),
            end_time=record.end_time.isoformat(),
            duration_ms=record.duration_ms,
            statistics=stats,
            language_distribution=summary_dict.get("language_distribution", {}),
            skipped_files=skipped,
            warnings=summary_dict.get("warnings", []),
            total_diagnostics_count=summary_dict.get("total_diagnostics_count", 0),
            files=files_list,
        )

    def get_diagnostics(self, db: Session, project_id: str, analysis_id: str) -> List[SyntaxDiagnostic]:
        """Collects all diagnostics across files for an analysis."""
        analysis = self.get_analysis_by_id(db, project_id, analysis_id)
        if not analysis:
            return []
        all_diags: List[SyntaxDiagnostic] = []
        for f in analysis.files:
            all_diags.extend(f.diagnostics)
        return all_diags


project_analysis_service = ProjectAnalysisService()
