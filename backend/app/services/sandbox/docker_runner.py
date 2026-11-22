import subprocess
import time
from pathlib import Path
from typing import Tuple, List, Optional
from app.core.logging import logger
from app.services.sandbox.execution_policy import ExecutionLimits


class DockerRunner:
    def execute(
        self,
        execution_id: str,
        image: str,
        staging_dir: Path,
        entrypoint_cmd: List[str],
        limits: ExecutionLimits,
    ) -> Tuple[int | None, str, str, bool, float]:
        """
        Executes a disposable Docker container with strict security parameters:
        Returns:
            (exit_code, stdout, stderr, is_timeout, duration_ms)
        """
        container_name = f"fixmate-sb-{execution_id}"
        posix_staging = staging_dir.resolve().as_posix()

        # Build security-hardened Docker command
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
            "-v",
            f"{posix_staging}:/workspace:ro",
            "-w",
            "/workspace",
            "-e",
            "PYTHONUNBUFFERED=1",
            "-e",
            "NODE_ENV=production",
            image,
        ] + entrypoint_cmd

        start_time = time.perf_counter()
        is_timeout = False
        exit_code = None
        stdout = ""
        stderr = ""

        try:
            logger.info(f"Starting sandbox container '{container_name}' with image '{image}'")
            proc = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
            )
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
            # Force remove container in case docker run hung
            self._force_remove_container(container_name)
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
