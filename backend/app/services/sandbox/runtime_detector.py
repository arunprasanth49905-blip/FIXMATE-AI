import shutil
import subprocess
import time
from typing import Optional, Tuple
from app.core.logging import logger


class RuntimeDetector:
    def __init__(self, cache_ttl_seconds: float = 5.0):
        self._cache_ttl = cache_ttl_seconds
        self._last_checked: float = 0.0
        self._cached_result: Optional[Tuple[bool, str, Optional[str], str]] = None

    def check_runtime(self, force_check: bool = False) -> Tuple[bool, str, Optional[str], str]:
        """
        Detects if the Docker container runtime is available and responding.
        Returns:
            (is_available: bool, runtime_name: str, version: Optional[str], status_message: str)
        """
        now = time.time()
        if not force_check and self._cached_result is not None and (now - self._last_checked) < self._cache_ttl:
            return self._cached_result

        docker_bin = shutil.which("docker.exe") or shutil.which("docker")
        if not docker_bin:
            res = (
                False,
                "docker",
                None,
                "Docker binary not found in system PATH. Sandbox execution requires Docker.",
            )
            self._cached_result = res
            self._last_checked = now
            return res

        # Check docker version
        version_str = None
        try:
            ver_proc = subprocess.run(
                [docker_bin, "--version"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if ver_proc.returncode == 0:
                version_str = ver_proc.stdout.strip()
        except Exception as e:
            logger.debug(f"Docker version query failed: {e}")

        # Check if docker daemon is alive
        try:
            info_proc = subprocess.run(
                [docker_bin, "info"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if info_proc.returncode == 0:
                res = (
                    True,
                    "docker",
                    version_str,
                    f"Docker container runtime is active ({version_str or 'ready'}).",
                )
            else:
                res = (
                    False,
                    "docker",
                    version_str,
                    "Docker CLI is installed, but Docker daemon is not running. Sandbox execution requires an active Docker engine.",
                )
        except subprocess.TimeoutExpired:
            res = (
                False,
                "docker",
                version_str,
                "Docker daemon check timed out after 3 seconds. Sandbox execution is unavailable.",
            )
        except Exception as e:
            res = (
                False,
                "docker",
                version_str,
                f"Docker daemon is unreachable: {type(e).__name__}. Sandbox execution is unavailable.",
            )

        self._cached_result = res
        self._last_checked = now
        return res


runtime_detector = RuntimeDetector()
