import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.sandbox import SandboxExecution
from app.services.sandbox.docker_runner import docker_runner
from app.services.sandbox.execution_policy import get_default_limits
from app.services.sandbox.runtime_detector import runtime_detector
from app.services.sandbox.test_runner_strategy import test_runner_strategy


@pytest.fixture
def sandbox_project(client: TestClient):
    """Fixture providing a project with Python and JavaScript source and test files."""
    tag = uuid.uuid4().hex[:6]
    name = f"Sandbox_Test_Project_{tag}"
    res = client.post("/api/v1/projects", json={"name": name, "language": "python"})
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # 1. Main python script
    py_code = 'print("Hello from Sandbox Python!")\nx = 10 + 20\nprint(f"Result: {x}")\n'
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "main.py", "content": py_code})

    # 2. Buggy python script
    bug_py = 'def divide():\n    return 100 / 0\ndivide()\n'
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "bug.py", "content": bug_py})

    # 3. Python test file
    test_py = 'def test_math():\n    assert 2 + 2 == 4\n\ndef test_sub():\n    assert 5 - 3 == 2\n'
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "tests/test_math.py", "content": test_py})

    # 4. JavaScript script
    js_code = 'console.log("Hello from Sandbox JS!");\nconsole.log("Count: " + (5 * 4));\n'
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "app.js", "content": js_code})

    # 5. TypeScript file
    ts_code = 'const msg: string = "Hello TypeScript";\nconsole.log(msg);\n'
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "index.ts", "content": ts_code})

    return proj_id


# =============================================================================
# 1. RUNTIME DETECTION & STATUS ENDPOINT
# =============================================================================


def test_sandbox_status_endpoint(client: TestClient):
    resp = client.get("/api/v1/sandbox/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert "runtime" in data
    assert "supported_languages" in data
    assert "Python" in data["supported_languages"]
    assert "JavaScript" in data["supported_languages"]
    assert "security_features" in data
    assert any("network none" in f.lower() for f in data["security_features"])


def test_runtime_detector_detects_unavailable():
    with patch("shutil.which", return_value=None):
        avail, runtime, ver, msg = runtime_detector.check_runtime(force_check=True)
        assert avail is False
        assert "not found" in msg.lower()


# =============================================================================
# 2. FAIL-CLOSED ARCHITECTURE (NO HOST FALLBACK)
# =============================================================================


def test_fail_closed_when_runtime_unavailable(client: TestClient, sandbox_project: str):
    """
    Critical Security Rule: If Docker runtime is unavailable, execution must fail closed
    with SANDBOX_UNAVAILABLE status. Never fall back to host execution.
    """
    with patch.object(
        runtime_detector,
        "check_runtime",
        return_value=(False, "docker", None, "Docker engine daemon is not running."),
    ):
        resp = client.post(
            f"/api/v1/projects/{sandbox_project}/execution/run",
            json={"file_path": "main.py"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SANDBOX_UNAVAILABLE"
        assert "Docker engine daemon is not running" in data["runtime_error"]
        assert data["exit_code"] is None
        assert data["stdout"] == ""


# =============================================================================
# 3. PATH CONFINEMENT & INPUT VALIDATION
# =============================================================================


def test_path_traversal_strictly_rejected(client: TestClient, sandbox_project: str):
    # Attempt .. path traversal
    resp = client.post(
        f"/api/v1/projects/{sandbox_project}/execution/run",
        json={"file_path": "../../../windows/system32/cmd.exe"},
    )
    assert resp.status_code == 400
    assert "traversal" in resp.json()["detail"].lower()


def test_nonexistent_file_rejected(client: TestClient, sandbox_project: str):
    resp = client.post(
        f"/api/v1/projects/{sandbox_project}/execution/run",
        json={"file_path": "does_not_exist.py"},
    )
    assert resp.status_code == 400
    assert "does not exist" in resp.json()["detail"].lower()


def test_nonexistent_project_rejected(client: TestClient):
    resp = client.post(
        f"/api/v1/projects/{uuid.uuid4()}/execution/run",
        json={"file_path": "main.py"},
    )
    assert resp.status_code == 404


def test_unsupported_language_rejection(client: TestClient, sandbox_project: str):
    # TypeScript is recognized but reports unsupported until safe in-container compilation is enabled
    resp = client.post(
        f"/api/v1/projects/{sandbox_project}/execution/run",
        json={"file_path": "index.ts"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "UNSUPPORTED"
    assert "TypeScript" in data["runtime_error"]


# =============================================================================
# 4. PYTHON & JAVASCRIPT CODE EXECUTION
# =============================================================================


def test_successful_python_execution(client: TestClient, sandbox_project: str):
    mock_run_result = (
        0,
        "Hello from Sandbox Python!\nResult: 30\n",
        "",
        False,
        125.4,
    )
    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_run_result) as mock_exec:
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/run",
                json={"file_path": "main.py"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "PASSED"
            assert data["exit_code"] == 0
            assert "Result: 30" in data["stdout"]
            assert data["timeout"] is False
            assert data["language"] == "Python"
            assert mock_exec.called


def test_successful_javascript_execution(client: TestClient, sandbox_project: str):
    mock_run_result = (
        0,
        "Hello from Sandbox JS!\nCount: 20\n",
        "",
        False,
        110.2,
    )
    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_run_result):
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/run",
                json={"file_path": "app.js"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "PASSED"
            assert data["language"] == "JavaScript"
            assert "Count: 20" in data["stdout"]


def test_runtime_error_captured(client: TestClient, sandbox_project: str):
    mock_run_result = (
        1,
        "",
        "Traceback (most recent call last):\n  File 'bug.py', line 2, in divide\nZeroDivisionError: division by zero\n",
        False,
        85.1,
    )
    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_run_result):
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/run",
                json={"file_path": "bug.py"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "FAILED"
            assert data["exit_code"] == 1
            assert "ZeroDivisionError" in data["stderr"]
            assert "ZeroDivisionError" in data["runtime_error"]


def test_timeout_enforcement(client: TestClient, sandbox_project: str):
    mock_timeout_result = (
        None,
        "",
        "Execution timed out",
        True,
        10005.0,
    )
    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_timeout_result):
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/run",
                json={"file_path": "main.py", "timeout_seconds": 10},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "TIMEOUT"
            assert data["timeout"] is True
            assert "timeout" in data["runtime_error"].lower()


# =============================================================================
# 5. TEST RUNNER EXECUTION
# =============================================================================


def test_execute_python_tests_success(client: TestClient, sandbox_project: str):
    pytest_stdout = (
        "tests/test_math.py::test_math PASSED\n"
        "tests/test_math.py::test_sub PASSED\n\n"
        "=== 2 passed in 0.12s ===\n"
    )
    mock_test_result = (0, pytest_stdout, "", False, 210.0)

    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_test_result):
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/tests",
                json={"test_file_path": "tests/test_math.py"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "PASSED"
            assert data["test_summary"] is not None
            assert data["test_summary"]["passed"] == 2
            assert data["test_summary"]["failed"] == 0
            assert data["test_summary"]["total"] == 2
            assert data["test_summary"]["framework"] == "pytest"


def test_execute_tests_missing_dependencies(client: TestClient, sandbox_project: str):
    mock_test_result = (1, "", "/usr/bin/python: No module named pytest\n", False, 45.0)

    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_test_result):
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/tests",
                json={"test_file_path": "tests/test_math.py"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "DEPENDENCIES_UNAVAILABLE"
            assert "pytest test framework is not installed" in data["test_summary"]["details"]


# =============================================================================
# 6. SECURITY ISOLATION & DOCKER COMMAND PARAMETERS
# =============================================================================


def test_docker_runner_enforces_security_flags(tmp_path: Path):
    """
    Verifies that docker_runner constructs the CLI arguments with full isolation:
    --network none, --memory, --read-only, --user 1000:1000, --cap-drop ALL,
    --security-opt no-new-privileges, -v <path>:/workspace:ro.
    """
    staging_file = tmp_path / "script.py"
    staging_file.write_text("print('test')")

    captured_cmds = []

    def mock_popen(cmd, **kwargs):
        captured_cmds.append(cmd)
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("test output", "")
        mock_proc.returncode = 0
        return mock_proc

    limits = get_default_limits()

    with patch("subprocess.Popen", side_effect=mock_popen):
        with patch("subprocess.run") as mock_run:
            docker_runner.execute(
                execution_id="test-sec-exec-123",
                image="python:3.13-slim",
                staging_dir=tmp_path,
                entrypoint_cmd=["python", "script.py"],
                limits=limits,
            )

    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]

    # Verify critical isolation flags
    assert "--network=none" in cmd
    assert "--read-only" in cmd
    assert f"--memory={limits.memory_mb}m" in cmd
    assert f"--memory-swap={limits.memory_mb}m" in cmd
    assert f"--cpus={limits.cpus}" in cmd
    assert f"--pids-limit={limits.pids}" in cmd
    assert "--user=1000:1000" in cmd
    assert "--cap-drop=ALL" in cmd
    assert "--security-opt=no-new-privileges" in cmd

    # Verify read-only staging mount
    mount_arg = [arg for arg in cmd if ":/workspace:ro" in arg]
    assert len(mount_arg) == 1

    # Verify zero host secrets exposed in env
    for arg in cmd:
        assert "GEMINI" not in arg
        assert "API_KEY" not in arg
        assert "DATABASE_URL" not in arg
        assert "docker.sock" not in arg


def test_output_truncation_limits():
    limits = get_default_limits()
    huge_text = "A" * (limits.max_output_bytes + 500)
    truncated = docker_runner._truncate(huge_text, limits.max_output_bytes)
    assert len(truncated.encode("utf-8")) < len(huge_text.encode("utf-8"))
    assert "[Output truncated at limit]" in truncated


# =============================================================================
# 7. EXECUTION HISTORY & PERSISTENCE
# =============================================================================


def test_execution_history_and_detail_retrieval(client: TestClient, sandbox_project: str):
    mock_run_result = (0, "Success run", "", False, 100.0)

    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_run_result):
            # Run code
            post_resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/run",
                json={"file_path": "main.py"},
            )
            assert post_resp.status_code == 200
            exec_id = post_resp.json()["id"]

    # Retrieve history
    hist_resp = client.get(f"/api/v1/projects/{sandbox_project}/execution/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total"] >= 1
    assert any(item["id"] == exec_id for item in hist_data["items"])

    # Retrieve detail
    detail_resp = client.get(f"/api/v1/projects/{sandbox_project}/execution/{exec_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == exec_id
    assert detail_resp.json()["status"] == "PASSED"
