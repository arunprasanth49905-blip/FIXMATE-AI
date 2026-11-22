import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import Tuple, List, Optional
from app.core.logging import logger
from app.services.sandbox.execution_policy import ExecutionLimits, get_default_limits

DIAGNOSTIC_LOG_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "docker_diagnostic.log"


def _record_diagnostic_stage(
    stage: str,
    cmd: List[str],
    pid: Optional[int],
    returncode: Optional[int],
    stdout: str,
    stderr: str,
    timeout: bool,
    duration_ms: float,
) -> None:
    """
    Temporary diagnostic logging as specified by Task 3:
    - Stage name (create/run/cp/start/logs/remove)
    - Command arguments (redacted)
    - PID
    - Return code
    - stdout
    - stderr
    - Timeout
    - Duration
    """
    redacted_cmd = []
    for arg in cmd:
        if any(secret in arg.upper() for secret in ["KEY", "SECRET", "TOKEN", "PASSWORD"]):
            redacted_cmd.append("[REDACTED]")
        else:
            redacted_cmd.append(arg)

    log_entry = (
        f"\n{'='*70}\n"
        f"STAGE:        {stage}\n"
        f"PID:          {pid}\n"
        f"RETURN CODE:  {returncode}\n"
        f"TIMEOUT:      {timeout}\n"
        f"DURATION MS:  {duration_ms:.2f}\n"
        f"COMMAND:      {' '.join(redacted_cmd)}\n"
        f"STDOUT:       {stdout.strip() if stdout else '(empty)'}\n"
        f"STDERR:       {stderr.strip() if stderr else '(empty)'}\n"
        f"{'='*70}\n"
    )

    logger.info(f"[DOCKER_STAGE_{stage.upper()}] rc={returncode} pid={pid} dur={duration_ms:.1f}ms err='{stderr.strip()}'")

    try:
        DIAGNOSTIC_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DIAGNOSTIC_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.warning(f"Failed to append to diagnostic log file: {e}")



class DockerRunner:
    def __init__(self):
        # Explicitly resolve Windows docker.exe to avoid accidentally invoking extensionless shell scripts on Windows
        self.docker_bin: str = shutil.which("docker.exe") or shutil.which("docker") or "docker"

    def execute(
        self,
        execution_id: str,
        image: str,
        staging_dir: Optional[Path] = None,
        entrypoint_cmd: Optional[List[str]] = None,
        limits: Optional[ExecutionLimits] = None,
        stdin_content: Optional[str] = None,
    ) -> Tuple[int | None, str, str, bool, float]:
        """
        Executes an isolated Docker container with strict security parameters:
        - Network disabled (--network none)
        - Memory and CPU quotas
        - Process ceilings (--pids-limit)
        - Non-root user (--user 1000:1000)
        - Dropped capabilities (--cap-drop ALL)
        - Security options (--security-opt no-new-privileges)
        - Zero Windows host directory mounts (-v)
        - DEVNULL or PIPE stdin preventing console interrupt / false exit code 130
        - Automatic container cleanup in finally block

        Supports two secure execution pathways:
        1. Stdin Code Delivery (stdin_content provided):
           Direct execution via 'docker run -i ...' with read-only rootfs and PIPE stdin.
        2. Isolated Container Workspace (staging_dir provided):
           Files transferred into container via 'docker create' + 'docker cp' + 'docker start -a'
           with DEVNULL stdin, avoiding any host filesystem volume mounts.

        Returns:
            (exit_code, stdout, stderr, is_timeout, duration_ms)
        """
        if limits is None:
            limits = get_default_limits()

        if entrypoint_cmd is None:
            entrypoint_cmd = []

        container_name = f"fixmate-sb-{execution_id}"
        start_time = time.perf_counter()
        is_timeout = False
        exit_code = None
        stdout = ""
        stderr = ""

        try:
            if stdin_content is not None:
                # =============================================================
                # Pathway 1: Stdin Code Delivery (zero host mounts, read-only root)
                # =============================================================
                docker_cmd = [
                    self.docker_bin,
                    "run",
                    "--rm",
                    "-i",
                    f"--name={container_name}",
                    "--network=none",
                    f"--memory={limits.memory_mb}m",
                    f"--memory-swap={limits.memory_mb}m",
                    f"--cpus={limits.cpus}",
                    f"--pids-limit={limits.pids}",
                    "--read-only",
                    "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
                    f"--user={limits.user}",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "-e",
                    "PYTHONUNBUFFERED=1",
                    "-e",
                    "NODE_ENV=production",
                    image,
                ] + entrypoint_cmd

                logger.info(f"Starting sandbox container '{container_name}' (stdin mode) with image '{image}'")
                t_sub_start = time.perf_counter()
                proc = subprocess.Popen(
                    docker_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                )
                try:
                    stdout, stderr = proc.communicate(input=stdin_content, timeout=limits.timeout_seconds)
                    exit_code = proc.returncode
                    sub_dur = (time.perf_counter() - t_sub_start) * 1000
                    _record_diagnostic_stage("run", docker_cmd, proc.pid, exit_code, stdout, stderr, False, sub_dur)
                except subprocess.TimeoutExpired:
                    is_timeout = True
                    sub_dur = (time.perf_counter() - t_sub_start) * 1000
                    logger.warning(f"Sandbox container '{container_name}' exceeded timeout of {limits.timeout_seconds}s. Terminating.")
                    try:
                        proc.kill()
                        stdout, stderr = proc.communicate(timeout=2)
                    except Exception:
                        pass
                    _record_diagnostic_stage("run", docker_cmd, proc.pid, -1, stdout or "", stderr or "", True, sub_dur)
                    self._force_remove_container(container_name)
                    exit_code = -1
                    stderr = f"Execution exceeded maximum timeout of {limits.timeout_seconds}s."

            elif staging_dir is not None:
                # =============================================================
                # Pathway 2: Isolated Container Workspace Copy (zero host mounts)
                # =============================================================
                create_cmd = [
                    self.docker_bin,
                    "create",
                    f"--name={container_name}",
                    "--network=none",
                    f"--memory={limits.memory_mb}m",
                    f"--memory-swap={limits.memory_mb}m",
                    f"--cpus={limits.cpus}",
                    f"--pids-limit={limits.pids}",
                    "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
                    "-w",
                    "/workspace",
                    f"--user={limits.user}",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "-e",
                    "PYTHONUNBUFFERED=1",
                    "-e",
                    "NODE_ENV=production",
                    image,
                ] + entrypoint_cmd

                logger.info(f"Creating isolated sandbox container '{container_name}' with image '{image}'")
                t_create_start = time.perf_counter()
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                res_create = subprocess.run(
                    create_cmd,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    check=False,
                    creationflags=creationflags,
                )
                create_dur = (time.perf_counter() - t_create_start) * 1000
                _record_diagnostic_stage(
                    stage="create",
                    cmd=create_cmd,
                    pid=None,
                    returncode=res_create.returncode,
                    stdout=res_create.stdout,
                    stderr=res_create.stderr,
                    timeout=False,
                    duration_ms=create_dur,
                )
                if res_create.returncode != 0:
                    logger.error(f"Failed to create container '{container_name}': {res_create.stderr}")
                    return res_create.returncode, "", f"Failed to create sandbox container: {res_create.stderr}", False, 0.0

                # Copy staged files directly into container /workspace
                posix_staging = staging_dir.resolve().as_posix()
                cp_cmd = [self.docker_bin, "cp", f"{posix_staging}/.", f"{container_name}:/workspace/"]
                t_cp_start = time.perf_counter()
                res_cp = subprocess.run(
                    cp_cmd,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                cp_dur = (time.perf_counter() - t_cp_start) * 1000
                _record_diagnostic_stage(
                    stage="cp",
                    cmd=cp_cmd,
                    pid=None,
                    returncode=res_cp.returncode,
                    stdout=res_cp.stdout,
                    stderr=res_cp.stderr,
                    timeout=False,
                    duration_ms=cp_dur,
                )
                if res_cp.returncode != 0:
                    logger.error(f"Failed to copy files to container '{container_name}': {res_cp.stderr}")
                    self._force_remove_container(container_name)
                    return res_cp.returncode, "", f"Failed to transfer source files into sandbox: {res_cp.stderr}", False, 0.0

                # Start container attached with DEVNULL stdin (never inherit console stdin)
                start_cmd = [self.docker_bin, "start", "-a", container_name]
                t_start_proc = time.perf_counter()
                proc = subprocess.Popen(
                    start_cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                )
                try:
                    stdout, stderr = proc.communicate(timeout=limits.timeout_seconds)
                    exit_code = proc.returncode
                    start_dur = (time.perf_counter() - t_start_proc) * 1000
                    _record_diagnostic_stage(
                        stage="start",
                        cmd=start_cmd,
                        pid=proc.pid,
                        returncode=exit_code,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=False,
                        duration_ms=start_dur,
                    )
                except subprocess.TimeoutExpired:
                    is_timeout = True
                    start_dur = (time.perf_counter() - t_start_proc) * 1000
                    logger.warning(f"Sandbox container '{container_name}' exceeded timeout of {limits.timeout_seconds}s. Terminating.")
                    try:
                        proc.kill()
                        stdout, stderr = proc.communicate(timeout=2)
                    except Exception:
                        pass
                    _record_diagnostic_stage(
                        stage="start",
                        cmd=start_cmd,
                        pid=proc.pid,
                        returncode=-1,
                        stdout=stdout or "",
                        stderr=stderr or "",
                        timeout=True,
                        duration_ms=start_dur,
                    )
                    self._force_remove_container(container_name)
                    exit_code = -1
                    stderr = f"Execution exceeded maximum timeout of {limits.timeout_seconds}s."

            else:
                # =============================================================
                # Pathway 3: Direct command execution with DEVNULL stdin
                # =============================================================
                docker_cmd = [
                    self.docker_bin,
                    "run",
                    "--rm",
                    f"--name={container_name}",
                    "--network=none",
                    f"--memory={limits.memory_mb}m",
                    f"--memory-swap={limits.memory_mb}m",
                    f"--cpus={limits.cpus}",
                    f"--pids-limit={limits.pids}",
                    "--read-only",
                    "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
                    f"--user={limits.user}",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "-e",
                    "PYTHONUNBUFFERED=1",
                    "-e",
                    "NODE_ENV=production",
                    image,
                ] + entrypoint_cmd

                proc = subprocess.Popen(
                    docker_cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                )
                try:
                    stdout, stderr = proc.communicate(timeout=limits.timeout_seconds)
                    exit_code = proc.returncode
                except subprocess.TimeoutExpired:
                    is_timeout = True
                    self._force_remove_container(container_name)
                    exit_code = -1
                    stderr = f"Execution exceeded maximum timeout of {limits.timeout_seconds}s."

        except Exception as e:
            logger.error(f"Sandbox container error for '{container_name}': {e}")
            stderr = f"Sandbox execution process error: {str(e)}"
            exit_code = -1
        finally:
            self._force_remove_container(container_name)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Truncate output streams if they exceed limit
        stdout = self._truncate(stdout or "", limits.max_output_bytes)
        stderr = self._truncate(stderr or "", limits.max_output_bytes)

        return exit_code, stdout, stderr, is_timeout, duration_ms

    def _force_remove_container(self, container_name: str) -> None:
        rm_cmd = [self.docker_bin, "rm", "-f", container_name]
        t_rm_start = time.perf_counter()
        try:
            res_rm = subprocess.run(
                rm_cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            rm_dur = (time.perf_counter() - t_rm_start) * 1000
            _record_diagnostic_stage(
                stage="remove",
                cmd=rm_cmd,
                pid=None,
                returncode=res_rm.returncode,
                stdout=res_rm.stdout,
                stderr=res_rm.stderr,
                timeout=False,
                duration_ms=rm_dur,
            )
        except Exception as e:
            rm_dur = (time.perf_counter() - t_rm_start) * 1000
            _record_diagnostic_stage(
                stage="remove",
                cmd=rm_cmd,
                pid=None,
                returncode=-1,
                stdout="",
                stderr=str(e),
                timeout=False,
                duration_ms=rm_dur,
            )

    def _truncate(self, text: str, max_bytes: int) -> str:
        if len(text.encode("utf-8", errors="replace")) > max_bytes:
            truncated = text[: max_bytes // 2]
            return truncated + "\n... [Output truncated at limit] ..."
        return text


docker_runner = DockerRunner()
