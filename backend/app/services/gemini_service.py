import re
import time
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.schemas.ai import AIStatusResponse, AITestResponse

# Redaction helper to ensure no credentials or raw tokens appear in errors
SECRET_PATTERN = re.compile(r"AIza[0-9A-Za-z-_]{35}|key=[a-zA-Z0-9_\-]+|api[-_]?key", re.IGNORECASE)


def sanitize_message(msg: str) -> str:
    if not msg:
        return ""
    return SECRET_PATTERN.sub("[REDACTED]", msg)


class GeminiService:
    def __init__(self):
        self._last_test_result: Optional[AITestResponse] = None

    def get_status(self) -> AIStatusResponse:
        is_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

        if not is_configured:
            return AIStatusResponse(
                provider="Google Gemini",
                configured=False,
                configured_model=settings.GEMINI_MODEL,
                connection_state="not_configured",
                message="Gemini API key is not configured. Add GEMINI_API_KEY in the backend .env file.",
            )

        if self._last_test_result is None:
            return AIStatusResponse(
                provider="Google Gemini",
                configured=True,
                configured_model=settings.GEMINI_MODEL,
                connection_state="configured_untested",
                message=f"Gemini API key is configured with model '{settings.GEMINI_MODEL}', but connection has not been verified yet.",
            )

        if self._last_test_result.success:
            return AIStatusResponse(
                provider="Google Gemini",
                configured=True,
                configured_model=settings.GEMINI_MODEL,
                connection_state="connected",
                message=f"Connection verified with model '{settings.GEMINI_MODEL}'. (Last test: {self._last_test_result.timestamp})",
            )

        return AIStatusResponse(
            provider="Google Gemini",
            configured=True,
            configured_model=settings.GEMINI_MODEL,
            connection_state="connection_failed",
            message=f"Last connection test failed: {self._last_test_result.message}",
        )

    def test_connection(self) -> AITestResponse:
        timestamp = datetime.now(timezone.utc).isoformat()
        is_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

        if not is_configured:
            result = AITestResponse(
                success=False,
                provider="Google Gemini",
                model=settings.GEMINI_MODEL,
                latency_ms=None,
                message="Gemini API key is not configured. Please set GEMINI_API_KEY in backend .env.",
                timestamp=timestamp,
                error="API_KEY_NOT_CONFIGURED",
            )
            self._last_test_result = result
            return result

        logger.info(f"Initiating Gemini connection test with model '{settings.GEMINI_MODEL}'...")
        start_time = time.perf_counter()
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                from google import genai
                from google.genai import errors

                # Initialize client with the configured key
                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                # Send a minimal, harmless ping test prompt
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents="Ping test for FIXMATE AI backend. Reply with 'PONG'.",
                )

                latency = round((time.perf_counter() - start_time) * 1000, 2)
                reply = response.text.strip() if response and response.text else "OK"

                result = AITestResponse(
                    success=True,
                    provider="Google Gemini",
                    model=settings.GEMINI_MODEL,
                    latency_ms=latency,
                    message=f"Connection successful ({latency}ms). Model response: {reply[:30]}",
                    timestamp=timestamp,
                    error=None,
                )
                self._last_test_result = result
                logger.info(f"Gemini connection test succeeded in {latency}ms.")
                return result

            except Exception as exc:
                raw_err = str(exc)
                safe_err = sanitize_message(raw_err)
                lower_err = safe_err.lower()

                # Retry transient errors (503 high demand, 429 rate limit, timeout)
                is_transient = (
                    "503" in safe_err
                    or "unavailable" in lower_err
                    or "high demand" in lower_err
                    or "429" in safe_err
                    or "resource_exhausted" in lower_err
                    or "timeout" in lower_err
                    or "deadline" in lower_err
                )
                if attempt < max_retries and is_transient:
                    sleep_time = (attempt + 1) * 2.0
                    logger.warning(
                        "Transient Gemini error on attempt %d: %s. Retrying in %.1fs...",
                        attempt + 1, safe_err, sleep_time
                    )
                    time.sleep(sleep_time)
                    continue

                latency = round((time.perf_counter() - start_time) * 1000, 2)
                logger.error(f"Gemini connection test failed: {safe_err}")

            error_type = "UNKNOWN_ERROR"
            user_msg = f"Connection failed: {safe_err}"

            # Categorize common errors safely
            lower_err = safe_err.lower()
            if "api key not valid" in lower_err or "api_key_invalid" in lower_err or "permission_denied" in lower_err or "403" in safe_err or "invalid_argument" in lower_err:
                error_type = "AUTHENTICATION_ERROR"
                user_msg = "Invalid or unauthorized API key. Check GEMINI_API_KEY in backend .env."
            elif "503" in safe_err or "unavailable" in lower_err or "high demand" in lower_err:
                error_type = "SERVICE_UNAVAILABLE"
                user_msg = f"Gemini API is currently experiencing high demand (503). Please retry in a moment."
            elif "model not found" in lower_err or ("not found" in lower_err and "model" in lower_err) or ("404" in safe_err and "not_found" in lower_err):
                error_type = "MODEL_NOT_FOUND"
                user_msg = f"Model '{settings.GEMINI_MODEL}' not found or unsupported."
            elif "resource_exhausted" in lower_err or "quota" in lower_err or "429" in safe_err or "rate limit" in lower_err:
                error_type = "QUOTA_EXCEEDED"
                user_msg = "API quota exceeded or rate limited. Please check your Gemini limits."
            elif "timeout" in safe_err.lower() or "deadline" in safe_err.lower():
                error_type = "TIMEOUT_ERROR"
                user_msg = "Request timed out while connecting to Gemini API."
            elif "connection" in safe_err.lower() or "failed to establish" in safe_err.lower():
                error_type = "NETWORK_ERROR"
                user_msg = "Network failure: Unable to reach Google Gemini API."

            result = AITestResponse(
                success=False,
                provider="Google Gemini",
                model=settings.GEMINI_MODEL,
                latency_ms=latency,
                message=user_msg,
                timestamp=timestamp,
                error=error_type,
            )
            self._last_test_result = result
            return result


gemini_service = GeminiService()
