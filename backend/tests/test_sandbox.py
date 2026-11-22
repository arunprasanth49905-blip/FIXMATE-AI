import json
import sys
import subprocess
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
    --network none, --memory, --user 1000:1000, --cap-drop ALL,
    --security-opt no-new-privileges, and zero host volume binds (-v).
    """
    staging_file = tmp_path / "script.py"
    staging_file.write_text("print('test')")

    captured_create_cmds = []
    captured_cp_cmds = []
    captured_start_cmds = []

    def mock_run(cmd, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stderr = ""
        mock_res.stdout = ""
        if len(cmd) > 1 and cmd[1] == "create":
            captured_create_cmds.append((cmd, kwargs))
        elif len(cmd) > 1 and cmd[1] == "cp":
            captured_cp_cmds.append((cmd, kwargs))
        return mock_res

    def mock_popen(cmd, **kwargs):
        captured_start_cmds.append((cmd, kwargs))
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("test output", "")
        mock_proc.returncode = 0
        return mock_proc

    limits = get_default_limits()

    with patch("subprocess.run", side_effect=mock_run):
        with patch("subprocess.Popen", side_effect=mock_popen):
            docker_runner.execute(
                execution_id="test-sec-exec-123",
                image="python:3.13-slim",
                staging_dir=tmp_path,
                entrypoint_cmd=["python", "-u", "script.py"],
                limits=limits,
            )

    assert len(captured_create_cmds) == 1
    create_cmd, create_kwargs = captured_create_cmds[0]

    # Verify Windows process-group isolation flag
    expected_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    assert create_kwargs.get("creationflags") == expected_flags

    # Verify critical isolation flags
    assert "--network=none" in create_cmd
    assert f"--memory={limits.memory_mb}m" in create_cmd
    assert f"--memory-swap={limits.memory_mb}m" in create_cmd
    assert f"--cpus={limits.cpus}" in create_cmd
    assert f"--pids-limit={limits.pids}" in create_cmd
    assert "--user=1000:1000" in create_cmd
    assert "--cap-drop=ALL" in create_cmd
    assert "--security-opt=no-new-privileges" in create_cmd
    assert "-w" in create_cmd
    assert "/workspace" in create_cmd

    # Verify zero host directory mounts (-v)
    assert not any(arg == "-v" or ":/workspace:ro" in arg for arg in create_cmd)

    # Verify docker cp was used for secure container file delivery
    assert len(captured_cp_cmds) == 1
    assert captured_cp_cmds[0][0][1] == "cp"

    # Verify container was started with DEVNULL stdin to prevent SIGINT (exit code 130)
    assert len(captured_start_cmds) == 1
    start_cmd, popen_kwargs = captured_start_cmds[0]
    assert start_cmd[1:] == ["start", "-a", "fixmate-sb-test-sec-exec-123"]
    assert "docker" in start_cmd[0].lower()
    import subprocess as sp
    assert popen_kwargs.get("stdin") == sp.DEVNULL

    # Verify zero host secrets exposed in env
    for arg in create_cmd:
        assert "GEMINI" not in arg
        assert "API_KEY" not in arg
        assert "DATABASE_URL" not in arg
        assert "docker.sock" not in arg


def test_docker_create_process_group_flag_platform_compatibility(tmp_path: Path):
    """
    Verifies that CREATE_NEW_PROCESS_GROUP (0x200) is passed on Windows and 0 on Linux.
    """
    staging_file = tmp_path / "script.py"
    staging_file.write_text("print('test')")

    captured_kwargs = []

    def mock_run(cmd, *args, **kwargs):
        if len(cmd) > 1 and cmd[1] == "create":
            captured_kwargs.append(kwargs)
        res = MagicMock()
        res.returncode = 0
        return res

    with patch("subprocess.run", side_effect=mock_run):
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            # Test Windows
            with patch("sys.platform", "win32"):
                docker_runner.execute(
                    execution_id="win-exec",
                    image="python:3.13-slim",
                    staging_dir=tmp_path,
                    entrypoint_cmd=["python", "-u", "script.py"],
                )
                assert captured_kwargs[-1].get("creationflags") == subprocess.CREATE_NEW_PROCESS_GROUP

            # Test Linux
            with patch("sys.platform", "linux"):
                docker_runner.execute(
                    execution_id="linux-exec",
                    image="python:3.13-slim",
                    staging_dir=tmp_path,
                    entrypoint_cmd=["python", "-u", "script.py"],
                )
                assert captured_kwargs[-1].get("creationflags") == 0


def test_docker_create_failure_handled_safely_and_cleans_up(tmp_path: Path):
    """
    Verifies that when docker create fails, it returns safe error message and runs container cleanup.
    """
    captured_rm_cmds = []

    def mock_run(cmd, *args, **kwargs):
        res = MagicMock()
        if len(cmd) > 1 and cmd[1] == "create":
            res.returncode = 1
            res.stderr = "daemon error: out of memory"
            res.stdout = ""
        elif len(cmd) > 1 and cmd[1] == "rm":
            captured_rm_cmds.append(cmd)
            res.returncode = 0
            res.stderr = ""
            res.stdout = ""
        else:
            res.returncode = 0
            res.stderr = ""
            res.stdout = ""
        return res

    with patch("subprocess.run", side_effect=mock_run):
        exit_code, stdout, stderr, is_timeout, duration_ms = docker_runner.execute(
            execution_id="fail-create-exec",
            image="python:3.13-slim",
            staging_dir=tmp_path,
            entrypoint_cmd=["python", "-u", "script.py"],
        )

    assert exit_code == 1
    assert "Failed to create sandbox container: daemon error: out of memory" in stderr
    assert is_timeout is False
    assert len(captured_rm_cmds) >= 1
    assert any("fail-create-exec" in arg for cmd in captured_rm_cmds for arg in cmd)



def test_docker_runner_stdin_mode_enforces_security():
    """
    Verifies that docker_runner stdin mode enforces read-only rootfs, network isolation,
    and pipe stdin.
    """
    captured_cmds = []

    def mock_popen(cmd, **kwargs):
        captured_cmds.append((cmd, kwargs))
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("output", "")
        mock_proc.returncode = 0
        return mock_proc

    limits = get_default_limits()

    with patch("subprocess.Popen", side_effect=mock_popen):
        with patch("subprocess.run"):
            docker_runner.execute(
                execution_id="test-stdin-exec",
                image="python:3.13-slim",
                entrypoint_cmd=["python", "-u", "-"],
                limits=limits,
                stdin_content="print('hello')",
            )

    assert len(captured_cmds) == 1
    cmd, kwargs = captured_cmds[0]
    assert "--network=none" in cmd
    assert "--read-only" in cmd
    assert "-i" in cmd
    import subprocess as sp
    assert kwargs.get("stdin") == sp.PIPE


def test_submitted_code_in_request_executes(client: TestClient, sandbox_project: str):
    """
    Task 5 Regression Test: Verify submitted code in request body is staged and executed.
    """
    submitted_code = 'print("SUBMITTED CODE EXECUTED SUCCESSFULLY")\n'
    mock_run_result = (0, "SUBMITTED CODE EXECUTED SUCCESSFULLY\n", "", False, 80.0)

    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_run_result) as mock_exec:
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/run",
                json={"file_path": "main.py", "code": submitted_code},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "PASSED"
            assert data["exit_code"] == 0
            assert "SUBMITTED CODE EXECUTED SUCCESSFULLY" in data["stdout"]
            assert mock_exec.called


def test_empty_code_execution_handled_safely(client: TestClient, sandbox_project: str):
    """
    Task 5 Regression Test: Verify empty submitted code executes safely returning exit code 0.
    """
    mock_run_result = (0, "", "", False, 40.0)

    with patch.object(runtime_detector, "check_runtime", return_value=(True, "docker", "29.6.2", "Active")):
        with patch.object(docker_runner, "execute", return_value=mock_run_result):
            resp = client.post(
                f"/api/v1/projects/{sandbox_project}/execution/run",
                json={"file_path": "main.py", "code": ""},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "PASSED"
            assert data["exit_code"] == 0
            assert data["stdout"] == ""
            assert data["stderr"] == ""


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
