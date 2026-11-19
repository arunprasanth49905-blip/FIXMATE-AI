import json
import re
import time
from typing import Optional, Tuple
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.schemas.repair import LLMRepairPayload
from app.services.gemini_service import sanitize_message
from app.services.repair.repair_context import RepairContext
from app.services.repair.repair_prompt_builder import (
    REPAIR_SYSTEM_PROMPT,
    build_repair_prompt,
)


class RepairEngine:
    """
    Dedicated AI code repair generation engine powered by Gemini 3.5 Flash Lite.
    Enforces structured JSON output and handles transient API retries safely.
    """

    def __init__(self):
        self.model = settings.GEMINI_MODEL

    def _extract_clean_json(self, raw_text: str) -> dict:
        """Extracts JSON object from response text, handling potential markdown fences."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse JSON directly from repair engine output: %s", exc)
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Unable to parse valid JSON from Gemini repair response: {exc}")

    def generate_repair(
        self,
        context: RepairContext,
        custom_instructions: Optional[str] = None,
    ) -> Tuple[LLMRepairPayload, float, str]:
        """
        Sends structured repair request to Google Gemini and parses validated payload.
        Returns (payload, duration_ms, raw_response_text).
        """
        if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gemini API key is not configured. Set GEMINI_API_KEY in backend .env.",
            )

        prompt = build_repair_prompt(context, custom_instructions)
        start_time = time.perf_counter()
        raw_text = ""
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                config = types.GenerateContentConfig(
                    system_instruction=REPAIR_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,  # Deterministic precision for code synthesis
                )

                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                if not response or not response.text:
                    raise ValueError("Empty response received from Gemini API during repair generation")

                raw_text = response.text.strip()
                break

            except Exception as exc:
                safe_err = sanitize_message(str(exc))
                lower_err = safe_err.lower()

                # Fail fast on auth / client errors
                if (
                    "api key not valid" in lower_err
                    or "api_key_invalid" in lower_err
                    or "permission_denied" in lower_err
                    or "403" in safe_err
                    or "invalid_argument" in lower_err
                ):
                    logger.error("Authentication error calling Gemini for repair: %s", safe_err)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or unauthorized Gemini API key.",
                    )

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
                    logger.warning("Transient Gemini error on attempt %d: %s. Retrying in %.1fs...", attempt + 1, safe_err, sleep_time)
                    time.sleep(sleep_time)
                    continue

                if "model not found" in lower_err or ("not_found" in lower_err and "model" in lower_err):
                    logger.error("Model not found error: %s", safe_err)
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Configured Gemini model '{self.model}' was not found.",
                    )

                logger.error("Failed to generate repair from Gemini: %s", safe_err)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Gemini API failure during repair generation: {safe_err}",
                )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Parse & Validate against schema
        try:
            parsed_json = self._extract_clean_json(raw_text)

            # Fallback field normalization
            summary = parsed_json.get("repair_summary") or parsed_json.get("summary") or "Targeted bug repair"
            explanation = parsed_json.get("repair_explanation") or parsed_json.get("explanation") or "Corrects detected defect."
            original = parsed_json.get("original_code") or context.exact_original_code
            proposed = parsed_json.get("proposed_code") or ""
            assumptions = parsed_json.get("assumptions") or []
            if not isinstance(assumptions, list):
                assumptions = [str(assumptions)]
            confidence = float(parsed_json.get("confidence", 90.0))
            repair_status = parsed_json.get("repair_status", "generated")

            payload = LLMRepairPayload(
                repair_summary=summary,
                repair_explanation=explanation,
                original_code=original,
                proposed_code=proposed,
                assumptions=[str(a) for a in assumptions],
                confidence=confidence,
                repair_status=repair_status if repair_status in ["generated", "needs_clarification"] else "generated",
            )
            return payload, duration_ms, raw_text

        except Exception as e:
            logger.error("Invalid structured repair response schema from Gemini: %s\nRaw: %s", e, raw_text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI returned malformed repair structure: {str(e)}",
            )
