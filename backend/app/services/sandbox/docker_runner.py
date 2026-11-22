import subprocess
import time
from pathlib import Path
from typing import Tuple, List, Optional
from app.core.logging import logger
from app.services.sandbox.execution_policy import ExecutionLimits, get_default_limits


class DockerRunner:
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
                    "docker",
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
                except subprocess.TimeoutExpired:
                    is_timeout = True
                    logger.warning(f"Sandbox container '{container_name}' exceeded timeout of {limits.timeout_seconds}s. Terminating.")
                    try:
                        proc.kill()
                        stdout, stderr = proc.communicate(timeout=2)
                    except Exception:
                        pass
                    self._force_remove_container(container_name)
                    exit_code = -1
                    stderr = f"Execution exceeded maximum timeout of {limits.timeout_seconds}s."

            elif staging_dir is not None:
                # =============================================================
                # Pathway 2: Isolated Container Workspace Copy (zero host mounts)
                # =============================================================
                create_cmd = [
                    "docker",
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
                res_create = subprocess.run(create_cmd, capture_output=True, text=True, check=False)
                if res_create.returncode != 0:
                    logger.error(f"Failed to create container '{container_name}': {res_create.stderr}")
                    return res_create.returncode, "", f"Failed to create sandbox container: {res_create.stderr}", False, 0.0

                # Copy staged files directly into container /workspace
                posix_staging = staging_dir.resolve().as_posix()
                res_cp = subprocess.run(
                    ["docker", "cp", f"{posix_staging}/.", f"{container_name}:/workspace/"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res_cp.returncode != 0:
                    logger.error(f"Failed to copy files to container '{container_name}': {res_cp.stderr}")
                    self._force_remove_container(container_name)
                    return res_cp.returncode, "", f"Failed to transfer source files into sandbox: {res_cp.stderr}", False, 0.0

                # Start container attached with DEVNULL stdin (never inherit console stdin)
                proc = subprocess.Popen(
                    ["docker", "start", "-a", container_name],
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
                    logger.warning(f"Sandbox container '{container_name}' exceeded timeout of {limits.timeout_seconds}s. Terminating.")
                    try:
                        proc.kill()
                        stdout, stderr = proc.communicate(timeout=2)
                    except Exception:
                        pass
                    self._force_remove_container(container_name)
                    exit_code = -1
                    stderr = f"Execution exceeded maximum timeout of {limits.timeout_seconds}s."

            else:
                # =============================================================
                # Pathway 3: Direct command execution with DEVNULL stdin
                # =============================================================
                docker_cmd = [
                    "docker",
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
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=3,
                check=False,
            )
        except Exception:
            pass

    def _truncate(self, text: str, max_bytes: int) -> str:
        if len(text.encode("utf-8", errors="replace")) > max_bytes:
            truncated = text[: max_bytes // 2]
            return truncated + "\n... [Output truncated at limit] ..."
        return text


docker_runner = DockerRunner()
