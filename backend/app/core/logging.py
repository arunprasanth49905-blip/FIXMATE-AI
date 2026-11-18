import logging
import re
import sys
from typing import Any

# Pattern to detect potential API keys / secrets for redaction
SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Standard Google API Key pattern
    re.compile(r"(key|secret|token|password)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9_\-]{8,})[\"']?", re.IGNORECASE)
]


class SecretRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.redact(v) if isinstance(v, str) else v for v in record.args)
        return True

    @staticmethod
    def redact(text: str) -> str:
        redacted = text
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        return redacted


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("fixmate")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(module)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactingFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
