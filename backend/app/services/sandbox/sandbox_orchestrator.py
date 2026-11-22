import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.project import Project
from app.models.sandbox import SandboxExecution
from app.schemas.sandbox import (
    ExecuteCodeRequest,
    ExecuteTestRequest,
    ResourceLimitsSchema,
    SandboxExecutionListResponse,
    SandboxExecutionResponse,
    SandboxStatusResponse,
    TestSummarySchema,
)
from app.services.sandbox.docker_runner import docker_runner
from app.services.sandbox.execution_policy import ExecutionLimits, get_default_limits
from app.services.sandbox.runtime_detector import runtime_detector
from app.services.sandbox.test_runner_strategy import test_runner_strategy


def get_utc_now():
    return datetime.now(timezone.utc)


class SandboxOrchestrator:
    def get_status(self) -> SandboxStatusResponse:
        """Checks and returns the current sandbox runtime health and availability."""
        is_avail, runtime_name, version, message = runtime_detector.check_runtime()
        return SandboxStatusResponse(
            available=is_avail,
            runtime=runtime_name,
            version=version,
            message=message,
            supported_languages=["Python", "JavaScript"],
        )

    def execute_code(
        self,
        db: Session,
        project_id: str,
        request: ExecuteCodeRequest,
    ) -> SandboxExecutionResponse:
        """
        Executes a specific source code file inside an isolated sandbox container.
        Strictly fails closed if the container runtime is unavailable.
        """
        execution_id = str(uuid.uuid4())
        start_time = get_utc_now()
        limits = get_default_limits(request.timeout_seconds)

        # 1. Validate project existence
        project = db.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        # 2. Path confinement and file validation
        clean_rel_path, abs_source_path = self._validate_and_resolve_path(project_id, request.file_path)

        # 3. Language detection
        language, image = self._resolve_language_and_image(clean_rel_path)
        if language == "TypeScript":
            return self._record_and_return_unsupported(
                db,
                execution_id=execution_id,
                project_id=project_id,
                file_path=clean_rel_path,
                language=language,
                execution_type="code",
                limits=limits,
                start_time=start_time,
                message="TypeScript direct runtime execution is not yet enabled. Transpile or execute JavaScript instead.",
            )
        elif language == "Unsupported":
            return self._record_and_return_unsupported(
                db,
                execution_id=execution_id,
                project_id=project_id,
                file_path=clean_rel_path,
                language=language,
                execution_type="code",
                limits=limits,
                start_time=start_time,
                message=f"File extension for '{clean_rel_path}' is not supported for sandbox runtime execution.",
            )

        # 4. Check container runtime availability (FAIL CLOSED)
        is_avail, runtime_name, _, status_msg = runtime_detector.check_runtime()
        if not is_avail:
            logger.warning(f"Sandbox execution rejected: {status_msg}")
            return self._record_and_return_sandbox_unavailable(
                db,
                execution_id=execution_id,
                project_id=project_id,
                file_path=clean_rel_path,
                language=language,
                execution_type="code",
                limits=limits,
                start_time=start_time,
                error_message=status_msg,
            )

        # 5. Prepare isolated ephemeral staging directory
        staging_dir = settings.get_sandbox_staging_dir(execution_id)
        cleanup_status = "cleaned"
        try:
            self._stage_project_files(project_id, staging_dir)

            # 6. Build entrypoint command
            if language == "Python":
                entrypoint = ["python", "-u", clean_rel_path]
            elif language == "JavaScript":
                entrypoint = ["node", clean_rel_path]
            else:
                entrypoint = [clean_rel_path]

            # 7. Execute in hardened container
            exit_code, stdout, stderr, is_timeout, duration_ms = docker_runner.execute(
                execution_id=execution_id,
                image=image,
                staging_dir=staging_dir,
                entrypoint_cmd=entrypoint,
                limits=limits,
            )

            # 8. Determine outcome status
            if is_timeout:
                status = "TIMEOUT"
                runtime_error = f"Execution exceeded maximum timeout of {limits.timeout_seconds}s."
            elif exit_code == 0:
                status = "PASSED"
                runtime_error = None
            else:
                status = "FAILED"
                runtime_error = self._extract_runtime_error(stderr or stdout)

        except Exception as e:
            logger.error(f"Sandbox orchestrator execution error: {e}")
            status = "ERROR"
            exit_code = -1
            stdout = ""
            stderr = f"Internal execution error: {str(e)}"
            runtime_error = str(e)
            is_timeout = False
            duration_ms = 0.0
        finally:
            # 9. Destroy temporary staging directory
            try:
                shutil.rmtree(staging_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up staging directory {staging_dir}: {e}")
                cleanup_status = "cleanup_failed"

        end_time = get_utc_now()

        # 10. Persist execution record in DB
        record = SandboxExecution(
            id=execution_id,
            project_id=project_id,
            file_path=clean_rel_path,
            language=language,
            execution_type="code",
            sandbox_runtime="docker",
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            runtime_error=runtime_error,
            timeout=is_timeout,
            duration_ms=duration_ms,
            start_time=start_time,
            end_time=end_time,
            resource_limits_json=json.dumps(self._limits_to_dict(limits)),
            cleanup_status=cleanup_status,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return self._to_response_schema(record, limits=limits)

    def execute_tests(
        self,
        db: Session,
        project_id: str,
        request: ExecuteTestRequest,
    ) -> SandboxExecutionResponse:
        """
        Executes a supported test file inside an isolated sandbox container.
        Strictly fails closed if the container runtime is unavailable.
        """
        execution_id = str(uuid.uuid4())
        start_time = get_utc_now()
        limits = get_default_limits(request.timeout_seconds)

        project = db.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        clean_rel_path, _ = self._validate_and_resolve_path(project_id, request.test_file_path)
        language, image = self._resolve_language_and_image(clean_rel_path)

        if language not in ("Python", "JavaScript"):
            return self._record_and_return_unsupported(
                db,
                execution_id=execution_id,
                project_id=project_id,
                file_path=clean_rel_path,
                language=language,
                execution_type="test",
                limits=limits,
                start_time=start_time,
                message=f"Test execution for language '{language}' is not supported.",
            )

        # Check runtime availability (FAIL CLOSED)
        is_avail, runtime_name, _, status_msg = runtime_detector.check_runtime()
        if not is_avail:
            logger.warning(f"Sandbox test execution rejected: {status_msg}")
            return self._record_and_return_sandbox_unavailable(
                db,
                execution_id=execution_id,
                project_id=project_id,
                file_path=clean_rel_path,
                language=language,
                execution_type="test",
                limits=limits,
                start_time=start_time,
                error_message=status_msg,
            )

        staging_dir = settings.get_sandbox_staging_dir(execution_id)
        cleanup_status = "cleaned"
        test_summary: Optional[TestSummarySchema] = None

        try:
            self._stage_project_files(project_id, staging_dir)
            entrypoint, _ = test_runner_strategy.get_test_command(
                language=language,
                test_file_name=clean_rel_path,
                test_case=request.test_case,
            )

            exit_code, stdout, stderr, is_timeout, duration_ms = docker_runner.execute(
                execution_id=execution_id,
                image=image,
                staging_dir=staging_dir,
                entrypoint_cmd=entrypoint,
                limits=limits,
            )

            if is_timeout:
                status = "TIMEOUT"
                runtime_error = f"Test execution exceeded maximum timeout of {limits.timeout_seconds}s."
                test_summary = TestSummarySchema(errors=1, details="Timeout exceeded during test execution.")
            else:
                status, test_summary = test_runner_strategy.parse_test_results(
                    language=language,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code if exit_code is not None else -1,
                )
                runtime_error = self._extract_runtime_error(stderr or stdout) if status != "PASSED" else None

        except Exception as e:
            logger.error(f"Sandbox test orchestrator error: {e}")
            status = "ERROR"
            exit_code = -1
            stdout = ""
            stderr = f"Internal test execution error: {str(e)}"
            runtime_error = str(e)
            is_timeout = False
            duration_ms = 0.0
        finally:
            try:
                shutil.rmtree(staging_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up staging directory {staging_dir}: {e}")
                cleanup_status = "cleanup_failed"

        end_time = get_utc_now()

        record = SandboxExecution(
            id=execution_id,
            project_id=project_id,
            file_path=clean_rel_path,
            language=language,
            execution_type="test",
            sandbox_runtime="docker",
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            runtime_error=runtime_error,
            timeout=is_timeout,
            duration_ms=duration_ms,
            start_time=start_time,
            end_time=end_time,
            resource_limits_json=json.dumps(self._limits_to_dict(limits)),
            test_summary_json=json.dumps(test_summary.model_dump()) if test_summary else None,
            cleanup_status=cleanup_status,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return self._to_response_schema(record, limits=limits, test_summary=test_summary)

    def list_executions(
        self,
        db: Session,
        project_id: str,
        limit: int = 50,
    ) -> SandboxExecutionListResponse:
        """Lists historical sandbox executions for a project, newest first."""
        query = (
            select(SandboxExecution)
            .where(SandboxExecution.project_id == project_id)
            .order_by(desc(SandboxExecution.created_at))
            .limit(limit)
        )
        records = db.execute(query).scalars().all()
        items = [self._to_response_schema(r) for r in records]
        return SandboxExecutionListResponse(total=len(items), items=items)

    def get_execution(
        self,
        db: Session,
        project_id: str,
        execution_id: str,
    ) -> Optional[SandboxExecutionResponse]:
        """Retrieves a single execution report."""
        query = select(SandboxExecution).where(
            SandboxExecution.project_id == project_id,
            SandboxExecution.id == execution_id,
        )
        record = db.execute(query).scalar_one_or_none()
        if not record:
            return None
        return self._to_response_schema(record)

    def _validate_and_resolve_path(self, project_id: str, file_path: str) -> Tuple[str, Path]:
        clean_rel = Path(file_path.strip()).as_posix().lstrip("/")
        if ".." in clean_rel.split("/"):
            raise ValueError("Path traversal sequences ('..') are strictly prohibited.")

        workspace_root = settings.get_workspace_dir(project_id)
        abs_path = (workspace_root / clean_rel).resolve()
        if not abs_path.is_relative_to(workspace_root):
            raise ValueError("Resolved file path points outside project workspace.")

        if not abs_path.is_file():
            raise ValueError(f"Source file '{clean_rel}' does not exist in project.")

        return clean_rel, abs_path

    def _resolve_language_and_image(self, file_path: str) -> Tuple[str, str]:
        ext = Path(file_path).suffix.lower()
        if ext in (".py", ".pyw"):
            return "Python", settings.SANDBOX_PYTHON_IMAGE
        elif ext in (".js", ".mjs", ".cjs"):
            return "JavaScript", settings.SANDBOX_JS_IMAGE
        elif ext in (".ts", ".tsx"):
            return "TypeScript", settings.SANDBOX_JS_IMAGE
        return "Unsupported", ""

    def _stage_project_files(self, project_id: str, staging_dir: Path) -> None:
        """Copies project files into the temporary sandbox staging directory."""
        workspace_dir = settings.get_workspace_dir(project_id)
        # Exclude internal / large directory trees
        shutil.copytree(
            workspace_dir,
            staging_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                "node_modules", ".git", ".venv", "venv", "__pycache__", ".fixmate"
            ),
        )

    def _extract_runtime_error(self, output: str) -> Optional[str]:
        if not output:
            return None
        lines = [line.strip() for line in output.strip().split("\n") if line.strip()]
        # Return the last relevant error or exception line
        for line in reversed(lines):
            if any(k in line for k in ("Error", "Exception", "Traceback", "FAILED", "AssertionError")):
                return line
        return lines[-1] if lines else None

    def _limits_to_dict(self, limits: ExecutionLimits) -> dict:
        return {
            "timeout_seconds": limits.timeout_seconds,
            "memory_mb": limits.memory_mb,
            "cpus": limits.cpus,
            "pids": limits.pids,
            "max_output_bytes": limits.max_output_bytes,
            "network_enabled": limits.network_enabled,
        }

    def _to_response_schema(
        self,
        record: SandboxExecution,
        limits: Optional[ExecutionLimits] = None,
        test_summary: Optional[TestSummarySchema] = None,
    ) -> SandboxExecutionResponse:
        limits_schema = None
        if limits:
            limits_schema = ResourceLimitsSchema(**self._limits_to_dict(limits))
        elif record.resource_limits_json:
            try:
                limits_schema = ResourceLimitsSchema(**json.loads(record.resource_limits_json))
            except Exception:
                pass

        if not test_summary and record.test_summary_json:
            try:
                test_summary = TestSummarySchema(**json.loads(record.test_summary_json))
            except Exception:
                pass

        return SandboxExecutionResponse(
            id=record.id,
            project_id=record.project_id,
            file_path=record.file_path,
            language=record.language,
            execution_type=record.execution_type,
            sandbox_runtime=record.sandbox_runtime,
            status=record.status,
            exit_code=record.exit_code,
            stdout=record.stdout or "",
            stderr=record.stderr or "",
            runtime_error=record.runtime_error,
            timeout=record.timeout,
            duration_ms=record.duration_ms,
            start_time=record.start_time,
            end_time=record.end_time,
            resource_limits=limits_schema,
            test_summary=test_summary,
            cleanup_status=record.cleanup_status,
            created_at=record.created_at,
        )

    def _record_and_return_sandbox_unavailable(
        self,
        db: Session,
        execution_id: str,
        project_id: str,
        file_path: str,
        language: str,
        execution_type: str,
        limits: ExecutionLimits,
        start_time: datetime,
        error_message: str,
    ) -> SandboxExecutionResponse:
        record = SandboxExecution(
            id=execution_id,
            project_id=project_id,
            file_path=file_path,
            language=language,
            execution_type=execution_type,
            sandbox_runtime="docker",
            status="SANDBOX_UNAVAILABLE",
            exit_code=None,
            stdout="",
            stderr="",
            runtime_error=error_message,
            timeout=False,
            duration_ms=0.0,
            start_time=start_time,
            end_time=get_utc_now(),
            resource_limits_json=json.dumps(self._limits_to_dict(limits)),
            cleanup_status="skipped",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._to_response_schema(record, limits=limits)

    def _record_and_return_unsupported(
        self,
        db: Session,
        execution_id: str,
        project_id: str,
        file_path: str,
        language: str,
        execution_type: str,
        limits: ExecutionLimits,
        start_time: datetime,
        message: str,
    ) -> SandboxExecutionResponse:
        record = SandboxExecution(
            id=execution_id,
            project_id=project_id,
            file_path=file_path,
            language=language,
            execution_type=execution_type,
            sandbox_runtime="docker",
            status="UNSUPPORTED",
            exit_code=None,
            stdout="",
            stderr="",
            runtime_error=message,
            timeout=False,
            duration_ms=0.0,
            start_time=start_time,
            end_time=get_utc_now(),
            resource_limits_json=json.dumps(self._limits_to_dict(limits)),
            cleanup_status="skipped",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._to_response_schema(record, limits=limits)


sandbox_orchestrator = SandboxOrchestrator()
