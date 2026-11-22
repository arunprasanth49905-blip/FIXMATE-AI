from dataclasses import dataclass
from app.core.config import settings


@dataclass
class ExecutionLimits:
    timeout_seconds: int = 10
    memory_mb: int = 256
    cpus: float = 1.0
    pids: int = 64
    max_output_bytes: int = 1024 * 1024  # 1 MB
    network_enabled: bool = False
    read_only_root: bool = True
    user: str = "1000:1000"


def get_default_limits(custom_timeout: int | None = None) -> ExecutionLimits:
    timeout = settings.SANDBOX_DEFAULT_TIMEOUT_SECONDS
    if custom_timeout is not None:
        timeout = max(1, min(custom_timeout, settings.SANDBOX_MAX_TIMEOUT_SECONDS))

    return ExecutionLimits(
        timeout_seconds=timeout,
        memory_mb=settings.SANDBOX_MAX_MEMORY_MB,
        cpus=settings.SANDBOX_MAX_CPUS,
        pids=settings.SANDBOX_MAX_PIDS,
        max_output_bytes=settings.SANDBOX_MAX_OUTPUT_BYTES,
        network_enabled=False,
        read_only_root=True,
        user="1000:1000",
    )
