import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models.detection import DetectionFinding, DetectionRun
from app.models.project import Project
from app.models.root_cause import RootCauseAnalysis
from app.schemas.root_cause import (
    AnalyzeFindingRequest,
    LLMRootCauseUpgradePayload,
)
from app.services.root_cause.root_cause_context import (
    RootCauseContextBuilder,
    redact_sensitive_data,
)
from app.services.root_cause.root_cause_engine import RootCauseEngine
from app.services.root_cause.root_cause_prompt_builder import (
    ROOT_CAUSE_SYSTEM_PROMPT,
    build_analysis_prompt,
)


# --- 1. Unit Tests: Context Extraction & Secret Redaction ---


def test_redact_sensitive_data():
    raw_code = (
        'gemini_key = "AIzaSyD-1234567890abcdefghijklmnopqrstuv"\n'
        'gh_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyzAB"\n'
        'auth = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"\n'
        'aws_key = "AKIA1234567890ABCDEF"\n'
        'password = "SuperSecretPassword123"\n'
    )
    redacted = redact_sensitive_data(raw_code)

    assert "AIzaSyD-1234567890abcdefghijklmnopqrstuv" not in redacted
    assert "[REDACTED_GEMINI_KEY]" in redacted
    assert "ghp_1234567890" not in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "[REDACTED_TOKEN]" in redacted
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "SuperSecretPassword123" not in redacted


def test_context_builder_padding_and_truncation(tmp_path, monkeypatch):
    project_id = "test-proj-ctx"
    workspace_dir = tmp_path / project_id
    workspace_dir.mkdir(parents=True)
    file_path = "script.py"
    target_file = workspace_dir / file_path

    lines = [f"line_{i} = {i}" for i in range(1, 51)]
    target_file.write_text("\n".join(lines), encoding="utf-8")

    from app.services.root_cause import root_cause_context

    monkeypatch.setattr(
        root_cause_context.file_service,
        "sanitize_and_resolve_path",
        lambda pid, rel: (target_file, rel),
    )

    # Finding at line 25
    snippet = RootCauseContextBuilder.build_finding_context(
        project_id=project_id,
        file_path=file_path,
        start_line=25,
        end_line=25,
        padding=5,
    )

    assert ">>>   25 | line_25 = 25" in snippet
    assert "   20 | line_20 = 20" in snippet
    assert "   30 | line_30 = 30" in snippet
    assert "line_10 =" not in snippet
    assert "line_45 =" not in snippet


def test_extract_exact_error_line(tmp_path, monkeypatch):
    project_id = "test-proj-exact"
    workspace_dir = tmp_path / project_id
    workspace_dir.mkdir(parents=True)
    file_path = "calc.py"
    target_file = workspace_dir / file_path

    code = "def discount(price):\n    return price * 0.1 / 0\n"
    target_file.write_text(code, encoding="utf-8")

    from app.services.root_cause import root_cause_context

    monkeypatch.setattr(
        root_cause_context.file_service,
        "sanitize_and_resolve_path",
        lambda pid, rel: (target_file, rel),
    )

    # Extract exact line 2
    exact_line = RootCauseContextBuilder.extract_exact_error_line(
        project_id=project_id,
        file_path=file_path,
        start_line=2,
        end_line=2,
    )
    assert exact_line == "return price * 0.1 / 0"

    # Line out of bounds
    oob = RootCauseContextBuilder.extract_exact_error_line(
        project_id=project_id,
        file_path=file_path,
        start_line=999,
        end_line=999,
    )
    assert "[Error line location unavailable]" in oob


# --- 2. Unit Tests: Prompt Builder & Safety Fencing ---


def test_build_analysis_prompt_safety():
    finding = DetectionFinding(
        id="f-123",
        run_id="run-1",
        project_id="p-1",
        rule_id="PY-W007",
        rule_name="Division by Zero",
        language="python",
        severity="high",
        confidence=0.98,
        category="correctness",
        file_path="main.py",
        start_line=2,
        start_column=1,
        end_line=2,
        end_column=25,
        message="Division by literal zero",
        explanation="Dividing any number by literal 0 always causes ZeroDivisionError.",
        evidence="price * discount / 0",
        remediation="Ensure denominator is non-zero.",
    )

    context = ">>>    2 | return price * discount / 0"
    exact_code = "return price * discount / 0"
    notes = "User reported ZeroDivisionError"

    prompt = build_analysis_prompt(
        finding,
        context,
        exact_buggy_code=exact_code,
        custom_user_notes=notes,
    )

    assert "PY-W007" in prompt
    assert "Division by Zero" in prompt
    assert "high" in prompt
    assert "<<<UNTRUSTED_SOURCE_SNIPPET>>>" in prompt
    assert "return price * discount / 0" in prompt
    assert "Developer notes: User reported ZeroDivisionError" in prompt
    assert "SIMPLE ENGLISH EXPLANATIONS" in ROOT_CAUSE_SYSTEM_PROMPT


# --- 3. Unit Tests: Engine JSON Extraction & Validation ---


def test_engine_extract_clean_json():
    engine = RootCauseEngine()

    raw_markdown = '```json\n{"bug_summary": "Division by zero", "confidence": 95.0}\n```'
    parsed = engine._extract_clean_json(raw_markdown)
    assert parsed["bug_summary"] == "Division by zero"
    assert parsed["confidence"] == 95.0

    bare_json = '{"bug_summary": "Bare summary", "confidence": 85.0}'
    parsed2 = engine._extract_clean_json(bare_json)
    assert parsed2["bug_summary"] == "Bare summary"


def test_engine_schema_and_calibration():
    sample_response = {
        "bug_summary": "Division by zero",
        "original_code": "return price * discount / 0",
        "simple_explanation": "This code divides a number by zero, which causes Python to stop with an error.",
        "root_cause": "The divisor is hardcoded as the number 0.",
        "corrected_code": "return price * discount / 100",
        "correction_explanation": "Assuming discount is a percentage, divide by 100 instead of zero.",
        "assumptions": ["The discount variable represents a percentage out of 100."],
        "severity": "high",
        "severity_reasoning": "High impact because function crashes unconditionally on call.",
        "confidence": 96.0,
        "confidence_reason": "Clear literal zero in division operator.",
        "fix_status": "suggested_not_applied",
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_response)
    mock_client.models.generate_content.return_value = mock_response

    finding = DetectionFinding(
        id="f-456",
        run_id="run-1",
        project_id="p-1",
        rule_id="PY-W007",
        rule_name="Division by Zero",
        language="python",
        severity="high",
        confidence=0.98,
        category="correctness",
        file_path="main.py",
        start_line=2,
        start_column=1,
        end_line=2,
        end_column=25,
        message="Division by literal zero",
        explanation="Dividing by zero causes exception.",
        evidence="return price * discount / 0",
        remediation="Change divisor",
    )

    with patch("google.genai.Client", return_value=mock_client):
        with patch("app.core.config.settings.GEMINI_API_KEY", "fake-key"):
            engine = RootCauseEngine()
            payload, duration_ms, raw_text = engine.analyze(
                finding=finding,
                context_snippet="context",
                exact_buggy_code="return price * discount / 0",
            )

            assert isinstance(payload, LLMRootCauseUpgradePayload)
            assert payload.bug_summary == "Division by zero"
            assert payload.original_code == "return price * discount / 0"
            assert payload.corrected_code == "return price * discount / 100"
            assert payload.severity == "high"
            assert payload.confidence == 96.0
            assert payload.fix_status == "suggested_not_applied"
            assert duration_ms >= 0


# --- 4. Integration Tests: API Endpoints & Service Workflow ---


def test_root_cause_api_full_lifecycle(client: TestClient):
    # 1. Create a Project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": "RCA Upgrade Project", "language": "python", "description": "Testing upgraded RCA"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Add source file with intentional bug
    file_content = (
        "def calculate_discount(price, discount):\n"
        "    return price * discount / 0\n"
    )
    file_resp = client.post(
        f"/api/v1/projects/{project_id}/files",
        json={"path": "pricing.py", "content": file_content},
    )
    assert file_resp.status_code == 201

    # 3. Create DetectionRun and Finding directly in DB
    db = SessionLocal()
    try:
        run = DetectionRun(
            project_id=project_id,
            status="completed_with_findings",
            total_findings=1,
            files_scanned=1,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        finding = DetectionFinding(
            run_id=run.id,
            project_id=project_id,
            rule_id="PY-W007",
            rule_name="Division by Zero",
            language="python",
            severity="high",
            confidence=0.98,
            category="correctness",
            file_path="pricing.py",
            start_line=2,
            start_column=12,
            end_line=2,
            end_column=32,
            message="Division by literal zero detected",
            explanation="Dividing any expression by literal 0 raises ZeroDivisionError.",
            evidence="return price * discount / 0",
            remediation="Change divisor to a non-zero value.",
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        finding_id = finding.id
    finally:
        db.close()

    # Mock Gemini response using upgraded schema
    mock_payload = LLMRootCauseUpgradePayload(
        bug_summary="Division by zero",
        original_code="return price * discount / 0",
        simple_explanation="This code attempts to divide a number by zero, which causes Python to stop immediately with a ZeroDivisionError.",
        root_cause="The code explicitly divides by the constant 0.",
        corrected_code="return price * discount / 100",
        correction_explanation="Divided by 100 instead of 0 to compute a percentage discount correctly.",
        assumptions=["Assumed 'discount' represents a percentage (e.g., 20 for 20%)."],
        severity="high",
        severity_reasoning="High severity because calling this function will always fail with an unhandled exception.",
        confidence=98.0,
        confidence_reason="Literal zero in division is a deterministic bug.",
        fix_status="suggested_not_applied",
    )

    with patch.object(
        RootCauseEngine,
        "analyze",
        return_value=(mock_payload, 120.0, '{"bug_summary": "mock"}'),
    ):
        # 4. Trigger Root Cause Analysis via API
        analyze_resp = client.post(
            f"/api/v1/projects/{project_id}/root-cause/analyze",
            json={
                "finding_id": finding_id,
                "include_surrounding_context": True,
                "custom_user_notes": "Occurs on checkout page",
            },
        )
        assert analyze_resp.status_code == 201
        data = analyze_resp.json()

        analysis_id = data["id"]
        # Verify Exact Error Location
        assert data["bug_location"]["file"] == "pricing.py"
        assert data["bug_location"]["line"] == 2
        assert data["bug_location"]["rule_id"] == "PY-W007"
        assert data["bug_location"]["language"] == "python"

        # Verify Simple Explanation & Code Correction
        assert data["original_code"] == "return price * discount / 0"
        assert "ZeroDivisionError" in data["simple_explanation"]
        assert data["root_cause"] == "The code explicitly divides by the constant 0."
        assert data["corrected_code"] == "return price * discount / 100"
        assert "100 instead of 0" in data["correction_explanation"]
        assert len(data["assumptions"]) == 1
        assert data["fix_status"] == "suggested_not_applied"

        # Verify Severity & Calibrated Confidence
        assert data["severity_assessment"]["detected_severity"] == "high"
        assert data["confidence_assessment"]["confidence_score"] == 98.0
        assert data["confidence_assessment"]["confidence_level"] == "HIGH"

        file_id = file_resp.json()["id"]

        # 5. Verify REPAIR SAFETY: Source code on disk is completely UNCHANGED
        file_check = client.get(f"/api/v1/projects/{project_id}/files/{file_id}")
        assert file_check.status_code == 200
        assert "return price * discount / 0" in file_check.json()["content"]

        # 6. Get Latest Analysis
        latest_resp = client.get(f"/api/v1/projects/{project_id}/root-cause/latest")
        assert latest_resp.status_code == 200
        assert latest_resp.json()["id"] == analysis_id
        assert latest_resp.json()["bug_location"]["line"] == 2

        # 7. Get History
        history_resp = client.get(f"/api/v1/projects/{project_id}/root-cause/history")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert history_data["total"] >= 1
        assert history_data["analyses"][0]["id"] == analysis_id
        assert history_data["analyses"][0]["original_code"] == "return price * discount / 0"

        # 8. Delete Analysis
        del_resp = client.delete(f"/api/v1/projects/{project_id}/root-cause/{analysis_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True


def test_root_cause_needs_clarification():
    sample_response = {
        "bug_summary": "Ambiguous variable assignment",
        "original_code": "data = process(val)",
        "simple_explanation": "The value passed to process is unknown.",
        "root_cause": "Cannot determine data schema without caller definitions.",
        "corrected_code": "",
        "correction_explanation": "Please provide the type of 'val' and the implementation of 'process'.",
        "assumptions": ["The parameter 'val' may be None or a dict."],
        "severity": "medium",
        "confidence": 65.0,
        "fix_status": "needs_clarification",
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_response)
    mock_client.models.generate_content.return_value = mock_response

    finding = DetectionFinding(
        id="f-789",
        run_id="run-1",
        project_id="p-1",
        rule_id="JS-W001",
        rule_name="Suspicious Equality",
        language="javascript",
        severity="medium",
        confidence=0.75,
        category="correctness",
        file_path="service.js",
        start_line=12,
        start_column=1,
        end_line=12,
        end_column=20,
        message="Suspicious check",
        explanation="Check may fail",
        evidence="data == null",
        remediation="Use ===",
    )

    with patch("google.genai.Client", return_value=mock_client):
        with patch("app.core.config.settings.GEMINI_API_KEY", "fake-key"):
            engine = RootCauseEngine()
            payload, duration_ms, raw_text = engine.analyze(
                finding=finding,
                context_snippet="context",
                exact_buggy_code="data = process(val)",
            )

            assert payload.fix_status == "needs_clarification"
            assert payload.confidence == 65.0
            assert payload.corrected_code == ""
            assert len(payload.assumptions) == 1
