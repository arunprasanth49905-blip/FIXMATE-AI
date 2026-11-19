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
    LLMRootCausePayload,
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
    # Setup test file in temporary project workspace
    project_id = "test-proj-ctx"
    workspace_dir = tmp_path / project_id
    workspace_dir.mkdir(parents=True)
    file_path = "script.py"
    target_file = workspace_dir / file_path

    # Create 50 lines
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

    # Line 20 to 30 should be present
    assert ">>>   25 | line_25 = 25" in snippet
    assert "   20 | line_20 = 20" in snippet
    assert "   30 | line_30 = 30" in snippet
    # Outside padding should not be present
    assert "line_10 =" not in snippet
    assert "line_45 =" not in snippet


# --- 2. Unit Tests: Prompt Builder & Safety Fencing ---


def test_build_analysis_prompt_safety():
    finding = DetectionFinding(
        id="f-123",
        run_id="run-1",
        project_id="p-1",
        rule_id="PY-E001",
        rule_name="Undefined Variable",
        language="python",
        severity="critical",
        confidence=0.95,
        category="correctness",
        file_path="main.py",
        start_line=10,
        start_column=1,
        end_line=10,
        end_column=15,
        message="Variable 'user_input' is used before assignment",
        explanation="Accessing undefined variable triggers NameError at runtime.",
        evidence="print(user_input)",
        remediation="Define variable prior to referencing.",
    )

    context = ">>>   10 | print(user_input)"
    notes = "User reported crash in production environment"

    prompt = build_analysis_prompt(finding, context, custom_user_notes=notes)

    assert "PY-E001" in prompt
    assert "Undefined Variable" in prompt
    assert "critical" in prompt
    assert "<<<UNTRUSTED_SOURCE_SNIPPET>>>" in prompt
    assert ">>>   10 | print(user_input)" in prompt
    assert "Developer notes: User reported crash in production environment" in prompt
    assert "ANALYSIS ONLY" in ROOT_CAUSE_SYSTEM_PROMPT


# --- 3. Unit Tests: Engine JSON Extraction & Validation ---


def test_engine_extract_clean_json():
    engine = RootCauseEngine()

    # Markdown fenced json
    raw_markdown = '```json\n{"summary": "Test summary", "confidence_score": 90.0}\n```'
    parsed = engine._extract_clean_json(raw_markdown)
    assert parsed["summary"] == "Test summary"
    assert parsed["confidence_score"] == 90.0

    # Bare json
    bare_json = '{"summary": "Bare summary", "confidence_score": 75.0}'
    parsed2 = engine._extract_clean_json(bare_json)
    assert parsed2["summary"] == "Bare summary"


def test_engine_schema_and_calibration():
    sample_response = {
        "summary": "Improper null check leading to TypeError",
        "bug_explanation": "Function assumes object property exists without validation.",
        "root_cause": "Missing defensive guard clause.",
        "technical_reasoning": "In JavaScript accessing property of undefined throws TypeError.",
        "trigger_conditions": ["When API payload omits 'profile' key"],
        "execution_impact": "Abrupt execution termination with uncaught exception.",
        "potential_consequences": ["500 Server Error", "Process crash"],
        "ai_assessed_severity": "high",
        "severity_reasoning": "High impact because it affects core login flow.",
        "recommended_approach": "Add optional chaining (?.) or early return guard.",
        "prevention": "Enable TypeScript strictNullChecks and add unit tests.",
        "missing_context": ["Caller request schema"],
        "confidence_score": 92.5,
        "confidence_level": "HIGH",
        "confidence_reason": "Clear AST structure with deterministic execution path.",
        "limitations": ["Runtime inputs cannot be fully determined statically."],
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_response)
    mock_client.models.generate_content.return_value = mock_response

    finding = DetectionFinding(
        id="f-456",
        run_id="run-1",
        project_id="p-1",
        rule_id="JS-E001",
        rule_name="Uncaught TypeError",
        language="javascript",
        severity="medium",
        confidence=0.85,
        category="correctness",
        file_path="app.js",
        start_line=5,
        start_column=1,
        end_line=5,
        end_column=20,
        message="Potential TypeError",
        explanation="Nullable property access",
        evidence="data.user.name",
        remediation="Use optional chaining",
    )

    with patch("google.genai.Client", return_value=mock_client):
        with patch("app.core.config.settings.GEMINI_API_KEY", "fake-key"):
            engine = RootCauseEngine()
            payload, duration_ms, raw_text = engine.analyze(finding, "context")

            assert isinstance(payload, LLMRootCausePayload)
            assert payload.summary == "Improper null check leading to TypeError"
            assert payload.ai_assessed_severity == "high"
            assert payload.confidence_score == 92.5
            assert payload.confidence_level == "HIGH"
            assert duration_ms >= 0


# --- 4. Integration Tests: API Endpoints & Service Workflow ---


def test_root_cause_api_full_lifecycle(client: TestClient):
    # 1. Create a Project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": "Root Cause Test Project", "language": "python", "description": "Testing RCA engine"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Add source file
    file_content = (
        "def compute_total(items):\n"
        "    for item in items:\n"
        "        total += item['price']  # Undefined variable 'total'\n"
        "    return total\n"
    )
    file_resp = client.post(
        f"/api/v1/projects/{project_id}/files",
        json={"path": "billing.py", "content": file_content},
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
            rule_id="PY-E001",
            rule_name="Undefined Variable Used",
            language="python",
            severity="critical",
            confidence=0.95,
            category="correctness",
            file_path="billing.py",
            start_line=3,
            start_column=9,
            end_line=3,
            end_column=14,
            message="Local variable 'total' referenced before assignment",
            explanation="Attempting to augment-assign 'total += ...' before 'total = 0' raises UnboundLocalError.",
            evidence="total += item['price']",
            remediation="Initialize total = 0 prior to the loop.",
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        finding_id = finding.id
    finally:
        db.close()

    # Mock Gemini response
    mock_payload = LLMRootCausePayload(
        summary="UnboundLocalError due to missing accumulator initialization",
        bug_explanation="The variable 'total' is augmented inside the loop without being initialized first.",
        root_cause="Missing variable declaration/initialization before loop scope.",
        technical_reasoning="Python compiler recognizes 'total' as local due to +=, causing UnboundLocalError when evaluating RHS.",
        trigger_conditions=["Executing compute_total with non-empty list"],
        execution_impact="Raises UnboundLocalError on first loop iteration, halting execution.",
        potential_consequences=["Fatal runtime exception", "Failed invoice generation"],
        ai_assessed_severity="critical",
        severity_reasoning="Critical because function is completely unusable at runtime.",
        recommended_approach="Initialize 'total = 0' immediately before the 'for' loop.",
        prevention="Use static linting or enable mypy/ruff checks.",
        missing_context=[],
        confidence_score=98.0,
        confidence_level="HIGH",
        confidence_reason="Standard static scoping rule violation in Python.",
        limitations=["None, isolated function scope."],
    )

    with patch.object(
        RootCauseEngine,
        "analyze",
        return_value=(mock_payload, 150.0, '{"summary": "mock"}'),
    ):
        # 4. Trigger Root Cause Analysis via API
        analyze_resp = client.post(
            f"/api/v1/projects/{project_id}/root-cause/analyze",
            json={
                "finding_id": finding_id,
                "include_surrounding_context": True,
                "custom_user_notes": "Occurs whenever checkout is attempted",
            },
        )
        assert analyze_resp.status_code == 201
        data = analyze_resp.json()

        analysis_id = data["id"]
        assert data["project_id"] == project_id
        assert data["finding_id"] == finding_id
        assert data["rule_id"] == "PY-E001"
        assert data["summary"] == "UnboundLocalError due to missing accumulator initialization"
        assert data["severity_assessment"]["detected_severity"] == "critical"
        assert data["severity_assessment"]["ai_assessed_severity"] == "critical"
        assert data["severity_assessment"]["severity_changed"] is False
        assert data["confidence_assessment"]["confidence_score"] == 98.0
        assert data["confidence_assessment"]["confidence_level"] == "HIGH"

        # 5. Get Latest Analysis
        latest_resp = client.get(f"/api/v1/projects/{project_id}/root-cause/latest")
        assert latest_resp.status_code == 200
        assert latest_resp.json()["id"] == analysis_id

        # 6. Get Analysis for Finding
        finding_resp = client.get(f"/api/v1/projects/{project_id}/root-cause/finding/{finding_id}")
        assert finding_resp.status_code == 200
        assert finding_resp.json()["id"] == analysis_id

        # 7. Get Analysis By ID
        id_resp = client.get(f"/api/v1/projects/{project_id}/root-cause/{analysis_id}")
        assert id_resp.status_code == 200
        assert id_resp.json()["id"] == analysis_id

        # 8. Get History
        history_resp = client.get(f"/api/v1/projects/{project_id}/root-cause/history")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert history_data["total"] >= 1
        assert history_data["analyses"][0]["id"] == analysis_id

        # 9. Delete Analysis
        del_resp = client.delete(f"/api/v1/projects/{project_id}/root-cause/{analysis_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        # Verify 404 after deletion
        get_deleted = client.get(f"/api/v1/projects/{project_id}/root-cause/{analysis_id}")
        assert get_deleted.status_code == 404


def test_root_cause_nonexistent_finding(client: TestClient):
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": "404 Test Proj", "language": "python"},
    )
    project_id = proj_resp.json()["id"]

    resp = client.post(
        f"/api/v1/projects/{project_id}/root-cause/analyze",
        json={"finding_id": "non-existent-finding-uuid"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
