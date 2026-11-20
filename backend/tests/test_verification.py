import json
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal, Base, engine
from app.models.project import Project, ProjectFile
from app.models.detection import DetectionRun, DetectionFinding
from app.models.repair import RepairProposal
from app.models.verification import RepairVerification
from app.services.repair.repair_context import compute_source_fingerprint
from app.services.repair.patch_generator import PatchGenerator
from app.services.verification.verification_service import verification_service


@pytest.fixture
def test_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    temp_ws_root = tempfile.mkdtemp(prefix="fixmate_p8_test_")
    orig_ws_root = settings.WORKSPACE_ROOT
    settings.WORKSPACE_ROOT = temp_ws_root

    proj_id = f"test-p8-{tempfile.mktemp()[-6:]}"
    project = Project(
        id=proj_id,
        name="Phase 8 Test Project",
        language="python",
    )
    db.add(project)
    db.commit()

    proj_dir = Path(temp_ws_root) / proj_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    yield {"db": db, "project": project, "proj_dir": proj_dir, "proj_id": proj_id}

    db.close()
    settings.WORKSPACE_ROOT = orig_ws_root
    shutil.rmtree(temp_ws_root, ignore_errors=True)


def create_applied_proposal(
    test_env,
    file_rel_path: str,
    original_code: str,
    repaired_code: str,
    rule_id: str = "PY-W007",
    rule_name: str = "Division by Zero",
    language: str = "python",
    status: str = "applied",
) -> RepairProposal:
    db = test_env["db"]
    proj_id = test_env["proj_id"]
    proj_dir = test_env["proj_dir"]

    # Write the repaired file to disk
    target_file = proj_dir / file_rel_path
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(repaired_code, encoding="utf-8")

    pre_fp = compute_source_fingerprint(original_code)
    post_fp = compute_source_fingerprint(repaired_code)

    file_rec = ProjectFile(
        project_id=proj_id,
        path=file_rel_path,
        name=Path(file_rel_path).name,
        extension=Path(file_rel_path).suffix,
        size=len(repaired_code.encode("utf-8")),
        is_directory=False,
    )
    db.add(file_rec)

    # Initial detection run
    det_run = DetectionRun(project_id=proj_id, status="completed", files_scanned=1, total_findings=1)
    db.add(det_run)
    db.flush()

    finding = DetectionFinding(
        run_id=det_run.id,
        project_id=proj_id,
        rule_id=rule_id,
        rule_name=rule_name,
        severity="high",
        category="correctness",
        file_path=file_rel_path,
        start_line=2,
        start_column=1,
        end_line=2,
        end_column=20,
        language=language,
        message="Deterministic bug finding",
        explanation="Testing automated verification",
        evidence=original_code.splitlines()[1] if len(original_code.splitlines()) > 1 else "",
        remediation="Fix the bug",
        confidence=0.98,
    )
    db.add(finding)
    db.flush()

    proposal = RepairProposal(
        project_id=proj_id,
        finding_id=finding.id,
        rule_id=rule_id,
        rule_name=rule_name,
        language=language,
        file_path=file_rel_path,
        start_line=2,
        end_line=2,
        source_fingerprint=pre_fp,
        repair_status=status,
        approval_status="approved",
        repair_summary="Fix target bug",
        repair_explanation="Replaces buggy code with clean fix",
        original_code=original_code.splitlines()[1] if len(original_code.splitlines()) > 1 else "",
        proposed_code=repaired_code.splitlines()[1] if len(repaired_code.splitlines()) > 1 else "",
        diff="--- a\n+++ b",
        additions=1,
        deletions=1,
        pre_apply_fingerprint=pre_fp,
        post_apply_fingerprint=post_fp,
        model="gemini-3.5-flash-lite",
        duration_ms=150.0,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


# =========================================================================
# Phase 8 Verification Tests
# =========================================================================

def test_verify_applied_python_repair_success(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    repaired = "def calc(x):\n    return x / 100\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["overall_status"] == "verified"
    assert data["syntax_status"] == "passed"
    assert data["target_bug_status"] == "resolved"
    assert data["regression_status"] == "passed"
    assert data["is_stale"] is False
    assert len(data["checks"]) == 5

    # Check comparison
    comp = data["comparison"]
    assert comp["target_rule_id"] == "PY-W007"
    assert comp["target_finding_status"] == "resolved"
    assert comp["regression_count"] == 0
    assert comp["resolved_count"] >= 1


def test_verify_python_syntax_failure(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    # Malformed syntax in repaired code
    repaired = "def calc(x):\n    return / 100\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["overall_status"] == "failed"
    assert data["syntax_status"] == "failed"
    syntax_check = next(c for c in data["checks"] if c["name"] == "syntax_verification")
    assert syntax_check["status"] == "failed"
    assert "SyntaxError" in syntax_check["message"] or "Syntax Error" in syntax_check["message"]


def test_verify_applied_javascript_repair_success(client, test_env):
    orig = "function run() {\n    try { doWork(); } catch (e) {}\n}\n"
    repaired = "function run() {\n    try { doWork(); } catch (e) { console.error(e); }\n}\n"
    proposal = create_applied_proposal(test_env, "script.js", orig, repaired, rule_id="JS-W002", rule_name="Empty Catch Block", language="javascript")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["overall_status"] == "verified"
    assert data["syntax_status"] == "passed"
    assert data["target_bug_status"] == "resolved"
    assert data["regression_status"] == "passed"


def test_verify_javascript_syntax_failure(client, test_env):
    orig = "function run() {\n    try { doWork(); } catch (e) {}\n}\n"
    repaired = "function run() {\n    try { doWork(); } catch (e) { console.error(e; }\n}\n"
    proposal = create_applied_proposal(test_env, "script.js", orig, repaired, rule_id="JS-W002", language="javascript")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["overall_status"] == "failed"
    assert data["syntax_status"] == "failed"


def test_verify_target_finding_still_present(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    # Still divides by 0!
    repaired = "def calc(x):\n    return (x + 1) / 0\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["overall_status"] == "failed"
    assert data["target_bug_status"] == "still_present"
    target_check = next(c for c in data["checks"] if c["name"] == "original_bug_resolution")
    assert target_check["status"] == "failed"
    assert "STILL PRESENT" in target_check["message"]


def test_verify_new_regression_finding_fails(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    # Fixes division by 0, but introduces an undefined variable reference (PY-W009: Undefined Variable, Critical)
    repaired = "def calc(x):\n    return unknown_undefined_var\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    # Undefined variable is Critical severity in Phase 4 -> triggers regression failure
    assert data["overall_status"] == "failed"
    assert data["regression_status"] == "failed"
    assert data["comparison"]["regression_count"] >= 1
    assert any(f["rule_id"] == "PY-W009" for f in data["comparison"]["new_findings"])


def test_verify_stale_source_detection(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    repaired = "def calc(x):\n    return x / 100\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007")

    # Now modify the file on disk so fingerprint mismatches post_apply_fingerprint!
    disk_file = test_env["proj_dir"] / "calc.py"
    disk_file.write_text("def calc(x):\n    # user edited later\n    return x * 2\n", encoding="utf-8")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["overall_status"] == "stale"
    assert data["is_stale"] is True
    integrity_check = next(c for c in data["checks"] if c["name"] == "applied_integrity")
    assert integrity_check["status"] == "failed"
    assert "STALE SOURCE" in integrity_check["message"]


def test_verify_unapplied_proposal_blocked(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    repaired = "def calc(x):\n    return x / 100\n"
    # Create proposal with status 'approved' (not yet applied)
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007", status="approved")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 400
    assert "requires an applied repair" in res.json()["detail"].lower()


def test_verify_unsupported_language_partial(client, test_env):
    orig = "puts 'hello'\n"
    repaired = "puts 'world'\n"
    proposal = create_applied_proposal(test_env, "script.rb", orig, repaired, rule_id="RB-001", language="ruby")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["overall_status"] == "partial"
    assert data["syntax_status"] == "skipped"


def test_verify_path_traversal_blocked(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    repaired = "def calc(x):\n    return x / 100\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired)

    # Maliciously alter proposal file_path to escape workspace
    proposal.file_path = "../../outside.py"
    test_env["db"].commit()

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code in (403, 404)


def test_verification_history_and_retrieval(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    repaired = "def calc(x):\n    return x / 100\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007")

    # Run verification twice
    res1 = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res1.status_code == 200
    id1 = res1.json()["id"]

    res2 = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res2.status_code == 200
    id2 = res2.json()["id"]

    assert id1 != id2

    # Get history
    hist_res = client.get(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verification-history")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["total"] >= 2
    assert any(v["id"] == id1 for v in hist_data["verifications"])
    assert any(v["id"] == id2 for v in hist_data["verifications"])

    # Get by ID
    single_res = client.get(f"/api/v1/projects/{test_env['proj_id']}/verification/{id1}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == id1


def test_source_remains_unmodified_after_verification(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    repaired = "def calc(x):\n    return x / 100\n"
    proposal = create_applied_proposal(test_env, "calc.py", orig, repaired, rule_id="PY-W007")

    disk_file = test_env["proj_dir"] / "calc.py"
    content_before = disk_file.read_text(encoding="utf-8")
    hash_before = compute_source_fingerprint(content_before)

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/verify")
    assert res.status_code == 200

    content_after = disk_file.read_text(encoding="utf-8")
    hash_after = compute_source_fingerprint(content_after)

    assert content_before == content_after
    assert hash_before == hash_after
