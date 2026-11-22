from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SandboxStatusResponse(BaseModel):
    available: bool
    runtime: str
    version: Optional[str] = None
    message: str
    supported_languages: List[str] = Field(default_factory=lambda: ["Python", "JavaScript"])
    security_features: List[str] = Field(
        default_factory=lambda: [
            "Network disabled (--network none)",
            "Read-only root filesystem (--read-only)",
            "Non-root unprivileged user (--user 1000:1000)",
            "Dropped capabilities (--cap-drop ALL)",
            "No new privileges (--security-opt no-new-privileges)",
            "Process limit (--pids-limit)",
            "RAM limit (--memory)",
            "CPU quota (--cpus)",
            "Ephemeral staging copy (original files untouched)",
            "Automatic container and staging cleanup",
        ]
    )


class ExecuteCodeRequest(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=500, description="Relative project path of file to execute")
    code: Optional[str] = Field(None, description="Optional submitted source code to execute")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=60, description="Optional custom execution timeout in seconds")


class ExecuteTestRequest(BaseModel):
    test_file_path: str = Field(..., min_length=1, max_length=500, description="Relative project path of test file")
    test_case: Optional[str] = Field(None, max_length=200, description="Optional specific test case/function name")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=60, description="Optional custom test execution timeout in seconds")


class ResourceLimitsSchema(BaseModel):
    timeout_seconds: int = 10
    memory_mb: int = 256
    cpus: float = 1.0
    pids: int = 64
    max_output_bytes: int = 1024 * 1024
    network_enabled: bool = False


class TestSummarySchema(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    framework: str = "pytest"
    details: Optional[str] = None


class SandboxExecutionResponse(BaseModel):
    id: str
    project_id: str
    file_path: str
    language: str
    execution_type: str
    sandbox_runtime: str
    status: str  # PASSED, FAILED, ERROR, TIMEOUT, CANCELLED, UNSUPPORTED, DEPENDENCIES_UNAVAILABLE, SANDBOX_UNAVAILABLE
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    runtime_error: Optional[str] = None
    timeout: bool = False
    duration_ms: float = 0.0
    start_time: datetime
    end_time: Optional[datetime] = None
    resource_limits: Optional[ResourceLimitsSchema] = None
    test_summary: Optional[TestSummarySchema] = None
    cleanup_status: str = "cleaned"
    created_at: datetime

    model_config = {"from_attributes": True}


class SandboxExecutionListResponse(BaseModel):
    total: int
    items: List[SandboxExecutionResponse]
