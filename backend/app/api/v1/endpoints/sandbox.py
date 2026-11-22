from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.sandbox import (
    ExecuteCodeRequest,
    ExecuteTestRequest,
    SandboxExecutionListResponse,
    SandboxExecutionResponse,
    SandboxStatusResponse,
)
from app.services.sandbox.sandbox_orchestrator import sandbox_orchestrator

router = APIRouter(tags=["Sandbox Execution"])


@router.get("/sandbox/status", response_model=SandboxStatusResponse)
def get_sandbox_status():
    """
    Returns the real-time availability, runtime engine, and security profile of the sandbox execution engine.
    Does not expose sensitive host paths, credentials, or environment secrets.
    """
    return sandbox_orchestrator.get_status()


@router.post(
    "/projects/{project_id}/execution/run",
    response_model=SandboxExecutionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_project_code(
    project_id: str,
    request: ExecuteCodeRequest,
    db: Session = Depends(get_db),
):
    """
    Executes a specific source code file inside an isolated disposable container sandbox.
    Fails closed if the sandbox runtime is unavailable.
    """
    try:
        return sandbox_orchestrator.execute_code(db, project_id, request)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox execution dispatch failed: {str(e)}",
        )


@router.post(
    "/projects/{project_id}/execution/tests",
    response_model=SandboxExecutionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_project_tests(
    project_id: str,
    request: ExecuteTestRequest,
    db: Session = Depends(get_db),
):
    """
    Executes an approved test file using an in-container test runner (pytest or node:test).
    Fails closed if the sandbox runtime is unavailable.
    """
    try:
        return sandbox_orchestrator.execute_tests(db, project_id, request)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox test execution dispatch failed: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/execution/history",
    response_model=SandboxExecutionListResponse,
)
def get_execution_history(
    project_id: str,
    limit: int = Query(50, ge=1, le=100, description="Max execution records to return"),
    db: Session = Depends(get_db),
):
    """Retrieves previous sandbox execution records for a project."""
    return sandbox_orchestrator.list_executions(db, project_id, limit=limit)


@router.get(
    "/projects/{project_id}/execution/{execution_id}",
    response_model=SandboxExecutionResponse,
)
def get_execution_record(
    project_id: str,
    execution_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves a single execution report by execution ID."""
    record = sandbox_orchestrator.get_execution(db, project_id, execution_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution record '{execution_id}' not found.",
        )
    return record
