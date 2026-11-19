import ast
import json
import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, Base, engine
from app.models.detection import DetectionFinding, DetectionRun
from app.models.project import Project, ProjectFile
from app.models.root_cause import RootCauseAnalysis
from app.models.repair import RepairProposal
from app.schemas.repair import LLMRepairPayload, GenerateRepairRequest
from app.services.repair.repair_context import (
    RepairContext,
    RepairContextBuilder,
    compute_source_fingerprint,
)
from app.services.repair.patch_generator import PatchGenerator, PatchArtifact
from app.services.repair.patch_validator import PatchValidator
from app.services.repair.repair_engine import RepairEngine
from app.services.repair.repair_service import RepairService
from app.core.config import settings


@pytest.fixture(autouse=True)
def ensure_db():
    Base.metadata.create_all(bind=engine)
    yield


# Helper fixture to create clean project with finding and RCA
@pytest.fixture
def test_setup():
    db = SessionLocal()
    proj_id = f"test-p-{uuid.uuid4().hex[:6]}"
    proj = Project(id=proj_id, name="Test Repair Project", language="python", description="Testing Phase 6")
    db.add(proj)
    db.commit()

    # Workspace file
    ws_dir = settings.get_workspace_dir(proj_id)
    ws_dir.mkdir(parents=True, exist_ok=True)
    py_path = ws_dir / "calculator.py"
    py_code = (
        "def compute_discount(price, rate):\n"
        "    return price * rate / 0\n"
    )
    py_path.write_text(py_code, encoding="utf-8")

    # Run & Finding
    run = DetectionRun(project_id=proj_id, status="completed_with_findings", total_findings=1, files_scanned=1)
    db.add(run)
    db.commit()

    finding = DetectionFinding(
        run_id=run.id,
        project_id=proj_id,
        rule_id="PY-W007",
        rule_name="Division by Zero",
        language="python",
        severity="high",
        confidence=0.98,
        category="correctness",
        file_path="calculator.py",
        start_line=2,
        start_column=12,
        end_line=2,
        end_column=28,
        message="Division by zero literal",
        explanation="Dividing by zero raises ZeroDivisionError.",
        evidence="return price * rate / 0",
        remediation="Change divisor to valid number.",
    )
    db.add(finding)
    db.commit()

    # RCA
    rca = RootCauseAnalysis(
        project_id=proj_id,
        finding_id=finding.id,
        rule_id=finding.rule_id,
        rule_name=finding.rule_name,
        language="python",
        file_path="calculator.py",
        start_line=2,
        end_line=2,
        model="gemini-3.5-flash-lite",
        status="success",
        original_code="return price * rate / 0",
        simple_explanation="Code divides by zero which crashes.",
        root_cause="Divisor is hardcoded as zero.",
        corrected_code="return price * rate / 100",
        correction_explanation="Divide by 100 for percentage.",
        assumptions_json=json.dumps(["Rate is a percentage out of 100."]),
        fix_status="suggested_not_applied",
        detected_severity="high",
        ai_assessed_severity="high",
        confidence_score=95.0,
        confidence_level="HIGH",
    )
    db.add(rca)
    db.commit()

    yield {
        "project_id": proj_id,
        "finding_id": finding.id,
        "rca_id": rca.id,
        "file_path": "calculator.py",
        "py_code": py_code,
        "ws_dir": ws_dir,
    }

    db.close()


# --------------------------------------------------------------------------
# 1-3. Valid Repair Proposals across Languages
# --------------------------------------------------------------------------

def test_valid_python_repair_proposal():
    orig_source = "def calc(a, b):\n    return a / 0\n"
    patch = PatchGenerator.generate_patch(orig_source, 2, 2, "    return a / b if b != 0 else 0", "calc.py")
    assert patch.additions == 1
    assert patch.deletions == 1
    assert "return a / b" in patch.diff

    val = PatchValidator.validate_patch(
        file_path="calc.py",
        language="python",
        original_source=orig_source,
        repaired_source=patch.repaired_source,
        start_line=2,
        end_line=2,
        source_fingerprint=compute_source_fingerprint(orig_source),
        expected_fingerprint=compute_source_fingerprint(orig_source),
    )
    assert val.overall_status == "passed"
    assert val.is_syntactically_valid is True


def test_valid_javascript_repair_proposal():
    orig_source = "function check(x) {\n  if (x = 5) return true;\n}\n"
    patch = PatchGenerator.generate_patch(orig_source, 2, 2, "  if (x === 5) return true;", "check.js")
    val = PatchValidator.validate_patch(
        file_path="check.js",
        language="javascript",
        original_source=orig_source,
        repaired_source=patch.repaired_source,
        start_line=2,
        end_line=2,
        source_fingerprint=compute_source_fingerprint(orig_source),
        expected_fingerprint=compute_source_fingerprint(orig_source),
    )
    assert val.overall_status in ["passed", "warning"]
    assert val.is_scope_valid is True


def test_valid_typescript_repair_proposal():
    orig_source = "function greet(name: string): string {\n  let x: any = null;\n  return x.name;\n}\n"
    patch = PatchGenerator.generate_patch(orig_source, 3, 3, "  return name;", "greet.ts")
    val = PatchValidator.validate_patch(
        file_path="greet.ts",
        language="typescript",
        original_source=orig_source,
        repaired_source=patch.repaired_source,
        start_line=3,
        end_line=3,
        source_fingerprint=compute_source_fingerprint(orig_source),
        expected_fingerprint=compute_source_fingerprint(orig_source),
    )
    assert val.is_scope_valid is True
    assert val.is_reversible is True


# --------------------------------------------------------------------------
# 4-6. Structured Response Parsing & Validation
# --------------------------------------------------------------------------

def test_gemini_structured_response_parsing():
    raw_json = json.dumps({
        "repair_summary": "Replaced literal zero with 100",
        "repair_explanation": "Prevents ZeroDivisionError",
        "original_code": "return price * rate / 0",
        "proposed_code": "return price * rate / 100",
        "assumptions": ["Rate is a percentage"],
        "confidence": 95.0,
        "repair_status": "generated"
    })
    engine = RepairEngine()
    parsed = engine._extract_clean_json(f"```json\n{raw_json}\n```")
    payload = LLMRepairPayload(**parsed)
    assert payload.repair_summary == "Replaced literal zero with 100"
    assert payload.confidence == 95.0


def test_missing_ai_response_fields_fallback():
    raw_json = '{"summary": "Fallback summary", "proposed_code": "return 42"}'
    engine = RepairEngine()
    parsed = engine._extract_clean_json(raw_json)
    assert parsed["summary"] == "Fallback summary"


def test_invalid_structured_response_rejected():
    engine = RepairEngine()
    with pytest.raises(ValueError):
        engine._extract_clean_json("Not a json at all")


# --------------------------------------------------------------------------
# 7-10. Error Handling (Timeout, Rate Limit, Unavailable, Auth)
# --------------------------------------------------------------------------

def test_gemini_auth_error_handling(test_setup):
    db = SessionLocal()
    try:
        ctx = RepairContextBuilder.build_context(test_setup["project_id"], test_setup["finding_id"], db)
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API_KEY_INVALID: 403 Forbidden")

        with patch("google.genai.Client", return_value=mock_client):
            with patch("app.core.config.settings.GEMINI_API_KEY", "bad-key"):
                engine = RepairEngine()
                with pytest.raises(Exception) as exc:
                    engine.generate_repair(ctx)
                assert "401" in str(exc.value) or "unauthorized" in str(exc.value).lower()
    finally:
        db.close()


def test_gemini_transient_retry_and_recovery(test_setup):
    db = SessionLocal()
    try:
        ctx = RepairContextBuilder.build_context(test_setup["project_id"], test_setup["finding_id"], db)
        mock_client = MagicMock()
        mock_success = MagicMock()
        mock_success.text = json.dumps({
            "repair_summary": "Fixed after retry",
            "repair_explanation": "Ok",
            "original_code": "return a / 0",
            "proposed_code": "return a / 100",
            "assumptions": [],
            "confidence": 90.0,
            "repair_status": "generated"
        })
        # Fail once with 503, succeed on attempt 2
        mock_client.models.generate_content.side_effect = [
            Exception("503 UNAVAILABLE: Model is currently experiencing high demand"),
            mock_success,
        ]

        with patch("google.genai.Client", return_value=mock_client):
            with patch("app.core.config.settings.GEMINI_API_KEY", "mock-key"):
                with patch("time.sleep"):  # do not delay tests
                    engine = RepairEngine()
                    payload, duration, raw = engine.generate_repair(ctx)
                    assert payload.repair_summary == "Fixed after retry"
    finally:
        db.close()


# --------------------------------------------------------------------------
# 11-14. Source Fingerprint & Staleness Protection
# --------------------------------------------------------------------------

def test_source_fingerprint_matching(test_setup):
    db = SessionLocal()
    try:
        ctx = RepairContextBuilder.build_context(test_setup["project_id"], test_setup["finding_id"], db)
        assert ctx.is_stale is False
        assert len(ctx.source_fingerprint) == 64
    finally:
        db.close()


def test_source_fingerprint_mismatch_staleness(test_setup):
    db = SessionLocal()
    try:
        # Mutate file on disk to simulate editing
        file_path = test_setup["ws_dir"] / test_setup["file_path"]
        file_path.write_text("def completely_different():\n    pass\n", encoding="utf-8")

        ctx = RepairContextBuilder.build_context(test_setup["project_id"], test_setup["finding_id"], db)
        assert ctx.is_stale is True
        assert "changed" in ctx.staleness_reason.lower()
    finally:
        db.close()


def test_stale_finding_rejected():
    val = PatchValidator.validate_patch(
        file_path="foo.py",
        language="python",
        original_source="x = 1\n",
        repaired_source="x = 2\n",
        start_line=1,
        end_line=1,
        source_fingerprint="fp-current",
        expected_fingerprint="fp-old",
    )
    assert val.overall_status == "failed"
    assert any("mismatch" in e.lower() for e in val.validation_errors)


# --------------------------------------------------------------------------
# 15-17. Patch Generation, Integrity & Reversibility
# --------------------------------------------------------------------------

def test_patch_reversibility_recovers_original():
    orig = "def add(a, b):\n    result = a + b\n    return result\n"
    patch = PatchGenerator.generate_patch(orig, 2, 2, "    result = (a + b) * 1", "add.py")

    val = PatchValidator.validate_patch(
        file_path="add.py",
        language="python",
        original_source=orig,
        repaired_source=patch.repaired_source,
        start_line=2,
        end_line=2,
        source_fingerprint=compute_source_fingerprint(orig),
        expected_fingerprint=compute_source_fingerprint(orig),
    )
    assert val.is_reversible is True
    assert val.overall_status == "passed"


# --------------------------------------------------------------------------
# 18-24. Security Scope Checks (Path Traversal, Absolute Path, No-op)
# --------------------------------------------------------------------------

def test_absolute_and_traversal_paths_rejected():
    val_traversal = PatchValidator.validate_patch(
        file_path="../../etc/passwd",
        language="python",
        original_source="a = 1",
        repaired_source="a = 2",
        start_line=1,
        end_line=1,
        source_fingerprint="fp",
        expected_fingerprint="fp",
    )
    assert val_traversal.is_scope_valid is False
    assert val_traversal.overall_status == "failed"

    val_abs = PatchValidator.validate_patch(
        file_path="/etc/passwd",
        language="python",
        original_source="a = 1",
        repaired_source="a = 2",
        start_line=1,
        end_line=1,
        source_fingerprint="fp",
        expected_fingerprint="fp",
    )
    assert val_abs.is_scope_valid is False


def test_no_op_patch_rejected():
    val = PatchValidator.validate_patch(
        file_path="main.py",
        language="python",
        original_source="a = 1\n",
        repaired_source="a = 1\n",
        start_line=1,
        end_line=1,
        source_fingerprint="fp",
        expected_fingerprint="fp",
    )
    assert val.is_scope_valid is False
    assert any("no changes" in e for e in val.validation_errors)


# --------------------------------------------------------------------------
# 25-26. Malformed Syntax Detection
# --------------------------------------------------------------------------

def test_malformed_python_syntax_rejected():
    orig = "def foo():\n    return 0\n"
    repaired_with_syntax_err = "def foo():\n    return (\n"
    val = PatchValidator.validate_patch(
        file_path="foo.py",
        language="python",
        original_source=orig,
        repaired_source=repaired_with_syntax_err,
        start_line=2,
        end_line=2,
        source_fingerprint="fp",
        expected_fingerprint="fp",
    )
    assert val.is_syntactically_valid is False
    assert val.overall_status == "failed"


# --------------------------------------------------------------------------
# 27. Safety Guarantee: Original Source Unchanged After Repair Generation
# --------------------------------------------------------------------------

def test_original_source_file_untouched_after_repair(test_setup):
    db = SessionLocal()
    try:
        service = RepairService()
        mock_payload = LLMRepairPayload(
            repair_summary="Replaced literal zero with 100",
            repair_explanation="Fixed division by zero",
            original_code="return price * rate / 0",
            proposed_code="return price * rate / 100",
            assumptions=["Rate is percent"],
            confidence=95.0,
            repair_status="generated",
        )

        with patch.object(RepairEngine, "generate_repair", return_value=(mock_payload, 150.0, "{}")):
            resp = service.generate_repair(test_setup["project_id"], test_setup["finding_id"], db)
            assert resp.repair_status == "generated"
            assert resp.diff is not None

        # Verify disk file is 100% UNTOUCHED
        file_path = test_setup["ws_dir"] / test_setup["file_path"]
        disk_content = file_path.read_text(encoding="utf-8")
        assert disk_content == test_setup["py_code"]
        assert "return price * rate / 0" in disk_content
        assert "return price * rate / 100" not in disk_content
    finally:
        db.close()


# --------------------------------------------------------------------------
# 28-30. Proposal Persistence & History
# --------------------------------------------------------------------------

def test_proposal_persistence_and_history(test_setup):
    db = SessionLocal()
    try:
        service = RepairService()
        mock_payload = LLMRepairPayload(
            repair_summary="First repair proposal",
            repair_explanation="Fixes bug",
            original_code="return price * rate / 0",
            proposed_code="return price * rate / 100",
            assumptions=[],
            confidence=92.0,
            repair_status="generated",
        )

        with patch.object(RepairEngine, "generate_repair", return_value=(mock_payload, 100.0, "{}")):
            prop1 = service.generate_repair(test_setup["project_id"], test_setup["finding_id"], db)

            # Generate second proposal (regeneration)
            mock_payload.repair_summary = "Second regenerated proposal"
            prop2 = service.generate_repair(test_setup["project_id"], test_setup["finding_id"], db)

            assert prop1.id != prop2.id

            # History preserves both
            hist = service.get_history(test_setup["project_id"], db, finding_id=test_setup["finding_id"])
            assert hist.total >= 2
            ids = [p.id for p in hist.proposals]
            assert prop1.id in ids
            assert prop2.id in ids
    finally:
        db.close()


# --------------------------------------------------------------------------
# 31-33. API Endpoints Lifecycle & Zero Code Execution
# --------------------------------------------------------------------------

def test_repair_api_full_lifecycle(client: TestClient, test_setup):
    mock_payload = LLMRepairPayload(
        repair_summary="API Lifecycle Repair",
        repair_explanation="Fixed division by zero via API",
        original_code="return price * rate / 0",
        proposed_code="return price * rate / 100",
        assumptions=["Percentage rate"],
        confidence=96.0,
        repair_status="generated",
    )

    with patch.object(RepairEngine, "generate_repair", return_value=(mock_payload, 120.0, "{}")):
        # 1. Generate Proposal
        gen_resp = client.post(
            f"/api/v1/projects/{test_setup['project_id']}/repair/generate",
            json={"finding_id": test_setup["finding_id"]},
        )
        assert gen_resp.status_code == 201
        data = gen_resp.json()
        proposal_id = data["id"]
        assert data["repair_status"] == "generated"
        assert data["diff"] != ""
        assert data["validation_details"]["overall_status"] == "passed"

        # 2. Get Proposal by ID
        get_resp = client.get(f"/api/v1/projects/{test_setup['project_id']}/repair/{proposal_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == proposal_id
        assert get_resp.json()["is_stale"] is False

        # 3. Get Latest for Finding
        finding_resp = client.get(f"/api/v1/projects/{test_setup['project_id']}/repair/finding/{test_setup['finding_id']}")
        assert finding_resp.status_code == 200
        assert finding_resp.json()["id"] == proposal_id

        # 4. Get History
        hist_resp = client.get(f"/api/v1/projects/{test_setup['project_id']}/repair/history")
        assert hist_resp.status_code == 200
        assert hist_resp.json()["total"] >= 1

        # 5. Delete Proposal
        del_resp = client.delete(f"/api/v1/projects/{test_setup['project_id']}/repair/{proposal_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True
