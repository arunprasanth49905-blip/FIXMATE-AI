import json
import re
import time
from typing import Optional, Tuple
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.models.detection import DetectionFinding
from app.schemas.root_cause import LLMRootCauseUpgradePayload
from app.services.gemini_service import sanitize_message
from app.services.root_cause.root_cause_prompt_builder import (
    ROOT_CAUSE_SYSTEM_PROMPT,
    build_analysis_prompt,
)


class RootCauseEngine:
    """
    Orchestrates AI Root Cause Analysis by communicating with Google Gemini,
    enforcing concise developer-friendly explanations, safe code corrections,
    and calibrated confidence metrics.
    """

    ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info"}

    def __init__(self):
        self.model = settings.GEMINI_MODEL

    def _extract_clean_json(self, raw_text: str) -> dict:
        """Strips markdown code fences and returns parsed dictionary."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as jde:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                sub = cleaned[start_idx : end_idx + 1]
                return json.loads(sub)
            raise ValueError(f"Failed to parse LLM response as JSON: {str(jde)}")

    def analyze(
        self,
        finding: DetectionFinding,
        context_snippet: str,
        exact_buggy_code: Optional[str] = None,
        custom_user_notes: Optional[str] = None,
    ) -> Tuple[LLMRootCauseUpgradePayload, float, str]:
        """
        Executes Gemini generation with system instructions and JSON structured parsing.
        Returns: (validated_payload, latency_ms, raw_response_text)
        """
        if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API key is not configured. Please configure GEMINI_API_KEY in the backend .env file.",
            )

        prompt = build_analysis_prompt(
            finding=finding,
            context_snippet=context_snippet,
            exact_buggy_code=exact_buggy_code,
            custom_user_notes=custom_user_notes,
        )

        start_time = time.perf_counter()
        raw_text = ""
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                config = types.GenerateContentConfig(
                    system_instruction=ROOT_CAUSE_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,  # Analytical consistency
                )

                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                if not response or not response.text:
                    raise ValueError("Empty response received from Gemini API")

                raw_text = response.text.strip()
                break

            except Exception as exc:
                last_error = exc
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
                    logger.error("Authentication error calling Gemini: %s", safe_err)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or unauthorized Gemini API key. Check GEMINI_API_KEY.",
                    )

                # Transient errors: retry with backoff (503 high demand, 429 rate limit, timeout)
                if attempt < max_retries and (
                    "503" in safe_err
                    or "unavailable" in lower_err
                    or "high demand" in lower_err
                    or "429" in safe_err
                    or "resource_exhausted" in lower_err
                    or "timeout" in lower_err
                    or "deadline" in lower_err
                ):
                    sleep_time = (attempt + 1) * 2.0
                    logger.warning("Transient error on attempt %d: %s. Retrying in %.1fs...", attempt + 1, safe_err, sleep_time)
                    time.sleep(sleep_time)
                    continue

                if "model not found" in lower_err or ("not_found" in lower_err and "model" in lower_err):
                    logger.error("Model not found error: %s", safe_err)
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Configured Gemini model '{self.model}' was not found.",
                    )

                logger.error("Error executing Gemini root cause analysis (attempt %d): %s", attempt + 1, safe_err)
                if attempt == max_retries:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Gemini API request failed: {safe_err}",
                    )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Parse and validate JSON structure
        try:
            data = self._extract_clean_json(raw_text)
        except Exception as e:
            logger.error("Failed to parse Gemini root cause JSON: %s. Raw: %s", e, raw_text[:500])
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini returned invalid analysis structure: {str(e)}",
            )

        # Ensure original_code is populated from source if missing from LLM output
        if not data.get("original_code") or not str(data.get("original_code")).strip():
            data["original_code"] = exact_buggy_code or finding.evidence or ""

        # Normalize summary / simple explanation fields
        if not data.get("bug_summary"):
            data["bug_summary"] = data.get("summary") or finding.rule_name
        if not data.get("simple_explanation"):
            data["simple_explanation"] = data.get("bug_explanation") or finding.explanation

        # Ensure corrected code and explanation exist
        if "corrected_code" not in data:
            data["corrected_code"] = ""
        if not data.get("correction_explanation"):
            data["correction_explanation"] = data.get("recommended_approach") or "No detailed correction explanation provided."

        # Normalize severity
        sev = str(data.get("severity") or data.get("ai_assessed_severity") or "medium").lower()
        if sev not in self.ALLOWED_SEVERITIES:
            sev = finding.severity.lower() if finding.severity else "medium"
        data["severity"] = sev

        # Calibrate confidence
        try:
            raw_conf = data.get("confidence") if data.get("confidence") is not None else data.get("confidence_score", 90.0)
            score = float(raw_conf)
            score = max(0.0, min(100.0, score))
        except (ValueError, TypeError):
            score = 90.0
        data["confidence"] = score

        # Fix status normalization
        fix_status = str(data.get("fix_status", "suggested_not_applied")).strip()
        if fix_status not in {"suggested_not_applied", "needs_clarification"}:
            fix_status = "suggested_not_applied"
        data["fix_status"] = fix_status

        # Validate with Pydantic
        try:
            payload = LLMRootCauseUpgradePayload(**data)
            return payload, duration_ms, raw_text
        except Exception as ve:
            logger.error("Root cause schema validation failure: %s", ve)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini response did not conform to required schema: {str(ve)}",
            )
