import json
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.logging import logger
from app.models.project import Project
from app.models.detection import DetectionFinding
from app.models.root_cause import RootCauseAnalysis
from app.schemas.root_cause import (
    AnalyzeFindingRequest,
    RootCauseAnalysisResponse,
    RootCauseHistoryItem,
    RootCauseHistoryResponse,
    SeverityAssessment,
    ConfidenceAssessment,
)
from app.services.root_cause.root_cause_context import RootCauseContextBuilder
from app.services.root_cause.root_cause_engine import RootCauseEngine


class RootCauseService:
    def __init__(self, engine: Optional[RootCauseEngine] = None):
        self.engine = engine or RootCauseEngine()

    def _to_response_dto(self, record: RootCauseAnalysis) -> RootCauseAnalysisResponse:
        """Converts database model to rich API response DTO."""
        trigger_conditions = []
        potential_consequences = []
        missing_context = []
        limitations = []

        try:
            trigger_conditions = json.loads(record.trigger_conditions_json or "[]")
        except Exception:
            pass

        try:
            potential_consequences = json.loads(record.potential_consequences_json or "[]")
        except Exception:
            pass

        try:
            missing_context = json.loads(record.missing_context_json or "[]")
        except Exception:
            pass

        try:
            limitations = json.loads(record.limitations_json or "[]")
        except Exception:
            pass

        return RootCauseAnalysisResponse(
            id=record.id,
            project_id=record.project_id,
            finding_id=record.finding_id,
            detection_run_id=record.detection_run_id,
            rule_id=record.rule_id,
            rule_name=record.rule_name,
            language=record.language,
            file_path=record.file_path,
            start_line=record.start_line,
            end_line=record.end_line,
            model=record.model,
            created_at=record.created_at,
            duration_ms=record.duration_ms,
            status=record.status,
            summary=record.summary,
            bug_explanation=record.bug_explanation,
            root_cause=record.root_cause,
            technical_reasoning=record.technical_reasoning,
            trigger_conditions=trigger_conditions,
            execution_impact=record.execution_impact,
            potential_consequences=potential_consequences,
            severity_assessment=SeverityAssessment(
                detected_severity=record.detected_severity,
                ai_assessed_severity=record.ai_assessed_severity,
                severity_reasoning=record.severity_reasoning,
                severity_changed=record.severity_changed,
            ),
            recommended_approach=record.recommended_approach,
            prevention=record.prevention,
            missing_context=missing_context,
            confidence_assessment=ConfidenceAssessment(
                confidence_score=record.confidence_score,
                confidence_level=record.confidence_level,
                confidence_reason=record.confidence_reason,
                limitations=limitations,
            ),
            error_message=record.error_message,
        )

    def analyze_finding(
        self,
        db: Session,
        project_id: str,
        request: AnalyzeFindingRequest,
    ) -> RootCauseAnalysisResponse:
        """Conducts AI Root Cause Analysis on a target finding and stores results."""
        # 1. Verify project exists
        project = db.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found.",
            )

        # 2. Verify finding exists and belongs to this project
        finding = db.execute(
            select(DetectionFinding).where(
                DetectionFinding.id == request.finding_id,
                DetectionFinding.project_id == project_id,
            )
        ).scalar_one_or_none()
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection finding with ID '{request.finding_id}' not found in project '{project_id}'.",
            )

        # 3. Extract source context with surrounding lines
        context_snippet = ""
        if request.include_surrounding_context:
            context_snippet = RootCauseContextBuilder.build_finding_context(
                project_id=project_id,
                file_path=finding.file_path,
                start_line=finding.start_line,
                end_line=finding.end_line,
            )

        # 4. Invoke AI Root Cause Engine
        payload, duration_ms, raw_text = self.engine.analyze(
            finding=finding,
            context_snippet=context_snippet,
            custom_user_notes=request.custom_user_notes,
        )

        # 5. Persist analysis in SQLite
        severity_changed = payload.ai_assessed_severity.lower() != finding.severity.lower()

        analysis_record = RootCauseAnalysis(
            project_id=project_id,
            finding_id=finding.id,
            detection_run_id=finding.run_id,
            rule_id=finding.rule_id,
            rule_name=finding.rule_name,
            language=finding.language,
            file_path=finding.file_path,
            start_line=finding.start_line,
            end_line=finding.end_line,
            model=self.engine.model,
            duration_ms=duration_ms,
            status="success",
            summary=payload.summary,
            bug_explanation=payload.bug_explanation,
            root_cause=payload.root_cause,
            technical_reasoning=payload.technical_reasoning,
            trigger_conditions_json=json.dumps(payload.trigger_conditions),
            execution_impact=payload.execution_impact,
            potential_consequences_json=json.dumps(payload.potential_consequences),
            detected_severity=finding.severity,
            ai_assessed_severity=payload.ai_assessed_severity,
            severity_reasoning=payload.severity_reasoning,
            severity_changed=severity_changed,
            recommended_approach=payload.recommended_approach,
            prevention=payload.prevention,
            missing_context_json=json.dumps(payload.missing_context),
            confidence_score=payload.confidence_score,
            confidence_level=payload.confidence_level,
            confidence_reason=payload.confidence_reason,
            limitations_json=json.dumps(payload.limitations),
            raw_response=raw_text,
            error_message=None,
        )

        db.add(analysis_record)
        db.commit()
        db.refresh(analysis_record)

        logger.info(
            "AI Root Cause Analysis completed for finding %s (%s) in %.1fms",
            finding.id,
            finding.rule_id,
            duration_ms,
        )

        return self._to_response_dto(analysis_record)

    def get_analysis(self, db: Session, project_id: str, analysis_id: str) -> RootCauseAnalysisResponse:
        """Retrieves a single root cause analysis record by ID."""
        record = db.execute(
            select(RootCauseAnalysis).where(
                RootCauseAnalysis.id == analysis_id,
                RootCauseAnalysis.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Root cause analysis '{analysis_id}' not found in project '{project_id}'.",
            )

        return self._to_response_dto(record)

    def get_latest_analysis(self, db: Session, project_id: str) -> RootCauseAnalysisResponse:
        """Retrieves the most recent root cause analysis for the project."""
        record = db.execute(
            select(RootCauseAnalysis)
            .where(RootCauseAnalysis.project_id == project_id)
            .order_by(desc(RootCauseAnalysis.created_at))
            .limit(1)
        ).scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No root cause analyses found for project '{project_id}'.",
            )

        return self._to_response_dto(record)

    def get_analysis_for_finding(
        self, db: Session, project_id: str, finding_id: str
    ) -> Optional[RootCauseAnalysisResponse]:
        """Retrieves the latest root cause analysis for a specific finding, or None if not analyzed."""
        record = db.execute(
            select(RootCauseAnalysis)
            .where(
                RootCauseAnalysis.project_id == project_id,
                RootCauseAnalysis.finding_id == finding_id,
            )
            .order_by(desc(RootCauseAnalysis.created_at))
            .limit(1)
        ).scalar_one_or_none()

        if not record:
            return None

        return self._to_response_dto(record)

    def get_history(
        self, db: Session, project_id: str, limit: int = 50
    ) -> RootCauseHistoryResponse:
        """Lists historical root cause analyses for the project."""
        stmt = (
            select(RootCauseAnalysis)
            .where(RootCauseAnalysis.project_id == project_id)
            .order_by(desc(RootCauseAnalysis.created_at))
            .limit(limit)
        )
        records = db.execute(stmt).scalars().all()

        items = [
            RootCauseHistoryItem(
                id=r.id,
                project_id=r.project_id,
                finding_id=r.finding_id,
                rule_id=r.rule_id,
                rule_name=r.rule_name,
                file_path=r.file_path,
                start_line=r.start_line,
                summary=r.summary,
                detected_severity=r.detected_severity,
                ai_assessed_severity=r.ai_assessed_severity,
                confidence_score=r.confidence_score,
                confidence_level=r.confidence_level,
                created_at=r.created_at,
                duration_ms=r.duration_ms,
                status=r.status,
            )
            for r in records
        ]

        return RootCauseHistoryResponse(
            project_id=project_id,
            total=len(items),
            analyses=items,
        )

    def delete_analysis(self, db: Session, project_id: str, analysis_id: str) -> bool:
        """Deletes a specific root cause analysis record."""
        record = db.execute(
            select(RootCauseAnalysis).where(
                RootCauseAnalysis.id == analysis_id,
                RootCauseAnalysis.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Root cause analysis '{analysis_id}' not found.",
            )

        db.delete(record)
        db.commit()
        return True
