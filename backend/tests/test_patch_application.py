import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.session import SessionLocal, Base, engine
from app.models.project import Project, ProjectFile
from app.models.detection import DetectionRun, DetectionFinding
from app.models.root_cause import RootCauseAnalysis
from app.models.repair import RepairProposal, RepairBackup, RepairAuditLog
from app.services.repair.repair_context import compute_source_fingerprint
from app.services.repair.patch_generator import PatchGenerator
from app.services.repair.patch_validator import PatchValidator
from app.services.repair.patch_application_service import PatchApplicationService


@pytest.fixture
def test_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    temp_ws_root = tempfile.mkdtemp(prefix="fixmate_p7_test_")
    orig_ws_root = settings.WORKSPACE_ROOT
    settings.WORKSPACE_ROOT = temp_ws_root

    proj_id = f"test-p7-{tempfile.mktemp()[-6:]}"
    project = Project(
        id=proj_id,
        name="Phase 7 Test Project",
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


def create_test_proposal(
    test_env,
    file_rel_path: str,
    original_code: str,
    start_line: int,
    end_line: int,
    proposed_code: str,
    language: str = "python",
    initial_status: str = "proposed",
) -> RepairProposal:
    db = test_env["db"]
    proj_id = test_env["proj_id"]
    proj_dir = test_env["proj_dir"]

    target_file = proj_dir / file_rel_path
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(original_code, encoding="utf-8")

    fp = compute_source_fingerprint(original_code)

    file_rec = ProjectFile(
        project_id=proj_id,
        path=file_rel_path,
        name=Path(file_rel_path).name,
        size=len(original_code.encode("utf-8")),
        extension=Path(file_rel_path).suffix,
        is_directory=False,
    )
    db.add(file_rec)

    det_run = DetectionRun(project_id=proj_id, status="completed", files_scanned=1, total_findings=1)
    db.add(det_run)
    db.flush()

    finding = DetectionFinding(
        run_id=det_run.id,
        project_id=proj_id,
        rule_id="TEST-001",
        rule_name="Test Rule",
        severity="high",
        category="correctness",
        file_path=file_rel_path,
        start_line=start_line,
        start_column=1,
        end_line=end_line,
        end_column=20,
        language=language,
        message="Test bug finding",
        explanation="Testing patch application",
        evidence=original_code.splitlines()[start_line - 1] if original_code.splitlines() else "",
        remediation="Fix it",
        confidence=0.95,
    )
    db.add(finding)
    db.flush()

    patch_artifact = PatchGenerator.generate_patch(
        full_source_raw=original_code,
        start_line=start_line,
        end_line=end_line,
        proposed_code=proposed_code,
        file_path=file_rel_path,
    )

    proposal = RepairProposal(
        project_id=proj_id,
        finding_id=finding.id,
        rule_id="TEST-001",
        rule_name="Test Rule",
        language=language,
        file_path=file_rel_path,
        start_line=start_line,
        end_line=end_line,
        source_fingerprint=fp,
        repair_status=initial_status,
        approval_status="approved" if initial_status == "approved" else "pending",
        repair_summary="Fix test bug",
        repair_explanation="Replaces buggy line with tested correction",
        original_code=original_code.splitlines()[start_line - 1] if original_code.splitlines() else "",
        proposed_code=proposed_code,
        diff=patch_artifact.diff,
        additions=patch_artifact.additions,
        deletions=patch_artifact.deletions,
        model="gemini-3.5-flash-lite",
        duration_ms=120.0,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


# =========================================================================
# 1. Approval & Rejection Tests
# =========================================================================

def test_approve_valid_proposal(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    prop = "    return x / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop)

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/approve")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "approved"
    assert data["proposal_id"] == proposal.id
    assert "approved_at" in data

    # Verify DB record
    test_env["db"].refresh(proposal)
    assert proposal.repair_status == "approved"
    assert proposal.approval_status == "approved"
    assert proposal.approved_at is not None


def test_approve_stale_proposal_fails(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    prop = "    return x / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop)

    # Modify file on disk to make proposal stale
    file_path = test_env["proj_dir"] / "calc.py"
    file_path.write_text("def calc(x):\n    # modified externally\n    return x / 0\n", encoding="utf-8")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/approve")
    assert res.status_code == 409
    assert "STALE PROPOSAL" in res.json()["detail"]

    test_env["db"].refresh(proposal)
    assert proposal.repair_status == "stale"


def test_approve_already_applied_proposal_fails(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    prop = "    return x / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop, initial_status="applied")

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/approve")
    assert res.status_code == 409
    assert "already been applied" in res.json()["detail"]


def test_reject_proposal(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    prop = "    return x / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop)

    res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/reject")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "rejected"

    test_env["db"].refresh(proposal)
    assert proposal.repair_status == "rejected"
    assert proposal.approval_status == "rejected"
    assert proposal.rejected_at is not None


def test_rejected_proposal_cannot_be_applied(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    prop = "    return x / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop, initial_status="rejected")

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res.status_code == 400
    assert "rejected proposal" in res.json()["detail"]


def test_unapproved_proposal_cannot_be_applied(client, test_env):
    orig = "def calc(x):\n    return x / 0\n"
    prop = "    return x / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop, initial_status="proposed")

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res.status_code == 400
    assert "Approval Required" in res.json()["detail"]


# =========================================================================
# 2. Patch Application Tests (Python, JS, TS)
# =========================================================================

def test_apply_python_patch_success(client, test_env):
    orig = (
        "def compute_discount(price, rate):\n"
        "    return price * rate / 0\n"
        "\n"
        "def main():\n"
        "    print(compute_discount(50, 10))\n"
    )
    prop = "    return price * rate / 100"
    proposal = create_test_proposal(test_env, "pricing.py", orig, 2, 2, prop, initial_status="approved")

    # Target file before apply
    target_path = test_env["proj_dir"] / "pricing.py"
    pre_fp = compute_source_fingerprint(orig)

    # Also create an unrelated sibling file to ensure zero cross-file modifications
    sibling_path = test_env["proj_dir"] / "sibling.py"
    sibling_content = "# Sibling file that must not change\nx = 42\n"
    sibling_path.write_text(sibling_content, encoding="utf-8")

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "applied"
    assert data["syntax_validation_passed"] is True
    assert data["backup_id"] is not None
    assert data["backup_path"] is not None

    # Verify disk content was modified accurately
    new_content = target_path.read_text(encoding="utf-8")
    assert "return price * rate / 100" in new_content
    assert "return price * rate / 0" not in new_content

    # Verify sibling file is completely untouched
    assert sibling_path.read_text(encoding="utf-8") == sibling_content

    # Verify backup exists and is byte-for-byte identical to original
    backup_path = Path(data["backup_path"])
    assert backup_path.is_file()
    assert backup_path.read_text(encoding="utf-8") == orig

    # Verify DB state
    test_env["db"].refresh(proposal)
    assert proposal.repair_status == "applied"
    assert proposal.applied_at is not None
    assert proposal.pre_apply_fingerprint == pre_fp
    assert proposal.post_apply_fingerprint == compute_source_fingerprint(new_content)


def test_apply_javascript_patch_success(client, test_env):
    orig = (
        "function calculateTotal(price, tax) {\n"
        "    let total = price == tax ? 0 : price + tax;\n"
        "    return total;\n"
        "}\n"
    )
    prop = "    let total = price === tax ? 0 : price + tax;"
    proposal = create_test_proposal(test_env, "calculator.js", orig, 2, 2, prop, language="javascript", initial_status="approved")

    target_path = test_env["proj_dir"] / "calculator.js"

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "applied"

    new_content = target_path.read_text(encoding="utf-8")
    assert "price === tax" in new_content


def test_apply_typescript_patch_success(client, test_env):
    orig = (
        "interface User {\n"
        "    id: string;\n"
        "    name: string;\n"
        "}\n"
        "export function getUserId(user: User): string {\n"
        "    return user.id == null ? '' : user.id;\n"
        "}\n"
    )
    prop = "    return user.id === null ? '' : user.id;"
    proposal = create_test_proposal(test_env, "user.ts", orig, 6, 6, prop, language="typescript", initial_status="approved")

    target_path = test_env["proj_dir"] / "user.ts"

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "applied"

    new_content = target_path.read_text(encoding="utf-8")
    assert "user.id === null" in new_content


def test_duplicate_apply_rejected(client, test_env):
    orig = "def add(a, b):\n    return a + b\n"
    prop = "    return a + b + 0"
    proposal = create_test_proposal(test_env, "math_utils.py", orig, 2, 2, prop, initial_status="approved")

    # First apply succeeds
    res1 = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res1.status_code == 200

    # Second apply is rejected
    res2 = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res2.status_code == 409
    assert "already been applied" in res2.json()["detail"]


# =========================================================================
# 3. Security & Safety Tests
# =========================================================================

def test_apply_stale_fingerprint_blocked(client, test_env):
    orig = "def process(items):\n    return items[0]\n"
    prop = "    return items[0] if items else None"
    proposal = create_test_proposal(test_env, "process.py", orig, 2, 2, prop, initial_status="approved")

    # Modify file after approval
    target_path = test_env["proj_dir"] / "process.py"
    target_path.write_text("def process(items):\n    # modified after approval\n    return items[0]\n", encoding="utf-8")

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res.status_code == 409
    assert "STALE PROPOSAL" in res.json()["detail"]

    test_env["db"].refresh(proposal)
    assert proposal.repair_status == "stale"


def test_unconfirmed_apply_rejected(client, test_env):
    orig = "def run():\n    pass\n"
    prop = "    return True"
    proposal = create_test_proposal(test_env, "run.py", orig, 2, 2, prop, initial_status="approved")

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": False},
    )
    assert res.status_code == 400
    assert "Human confirmation is required" in res.json()["detail"]


def test_path_traversal_blocked_in_application(client, test_env):
    # Manually craft proposal with malicious path
    orig = "secret = 123"
    proposal = create_test_proposal(test_env, "safe.py", orig, 1, 1, "secret = 456", initial_status="approved")

    # Hack DB record to simulate tampered file_path
    proposal.file_path = "../../etc/passwd"
    test_env["db"].commit()

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert res.status_code in (400, 403)


# =========================================================================
# 4. Failure Recovery & Rollback Tests
# =========================================================================

def test_apply_rejects_syntactically_invalid_patch_prior_to_write(client, test_env):
    orig = "def valid_code():\n    return 42\n"
    # Malformed replacement with Python syntax error
    bad_prop = "    return 42 +++ ((("
    proposal = create_test_proposal(test_env, "fragile.py", orig, 2, 2, bad_prop, initial_status="approved")

    target_path = test_env["proj_dir"] / "fragile.py"
    pre_fp = compute_source_fingerprint(orig)

    res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    # Must fail validation prior to disk write
    assert res.status_code == 422
    assert "Patch validation failed" in res.json()["detail"]

    # Verify original file content was never touched
    assert target_path.read_text(encoding="utf-8") == orig
    assert compute_source_fingerprint(target_path.read_text(encoding="utf-8")) == pre_fp


def test_failure_recovery_restores_original_on_post_write_error(client, test_env):
    orig = "def valid_code():\n    return 42\n"
    prop = "    return 100"
    proposal = create_test_proposal(test_env, "recover.py", orig, 2, 2, prop, initial_status="approved")

    target_path = test_env["proj_dir"] / "recover.py"
    pre_fp = compute_source_fingerprint(orig)

    # Simulate unexpected syntax failure during post-write verification (e.g. disk corruption)
    with patch.object(PatchApplicationService, "_verify_applied_content", side_effect=ValueError("Simulated post-write corruption")):
        res = client.post(
            f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
            json={"confirm_application": True},
        )
        assert res.status_code == 422
        assert "restored from backup" in res.json()["detail"]

    # Verify original file content was safely restored byte-for-byte!
    restored_content = target_path.read_text(encoding="utf-8")
    assert restored_content == orig
    assert compute_source_fingerprint(restored_content) == pre_fp

    test_env["db"].refresh(proposal)
    assert proposal.repair_status == "failed"


def test_rollback_patch_success(client, test_env):
    orig = "def calculate(a, b):\n    return a / 0\n"
    prop = "    return a / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop, initial_status="approved")

    target_path = test_env["proj_dir"] / "calc.py"
    pre_fp = compute_source_fingerprint(orig)

    # 1. Apply patch
    apply_res = client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )
    assert apply_res.status_code == 200
    assert "return a / 100" in target_path.read_text(encoding="utf-8")

    # 2. Rollback patch
    rollback_res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/rollback")
    assert rollback_res.status_code == 200, rollback_res.text
    rb_data = rollback_res.json()
    assert rb_data["status"] == "rolled_back"
    assert rb_data["restored_fingerprint"] == pre_fp

    # Verify file on disk is restored byte-for-byte to original
    restored_content = target_path.read_text(encoding="utf-8")
    assert restored_content == orig
    assert "return a / 0" in restored_content

    test_env["db"].refresh(proposal)
    assert proposal.repair_status == "rolled_back"
    assert proposal.rollback_at is not None


def test_rollback_rejected_if_source_modified_after_application(client, test_env):
    orig = "def calculate(a, b):\n    return a / 0\n"
    prop = "    return a / 100"
    proposal = create_test_proposal(test_env, "calc.py", orig, 2, 2, prop, initial_status="approved")

    target_path = test_env["proj_dir"] / "calc.py"

    # 1. Apply patch
    client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )

    # 2. User edits file after patch application
    target_path.write_text("def calculate(a, b):\n    # user new manual edit\n    return a / 100\n", encoding="utf-8")

    # 3. Rollback must be rejected to prevent overwriting newer manual edits
    rollback_res = client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/rollback")
    assert rollback_res.status_code == 409
    assert "modified since the patch was applied" in rollback_res.json()["detail"]

    # Content must NOT be overwritten
    assert "user new manual edit" in target_path.read_text(encoding="utf-8")


# =========================================================================
# 5. Audit History Tests
# =========================================================================

def test_audit_history_lifecycle(client, test_env):
    orig = "def hello():\n    return 'bug'\n"
    prop = "    return 'fixed'"
    proposal = create_test_proposal(test_env, "hello.py", orig, 2, 2, prop, initial_status="proposed")

    # 1. Approve
    client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/approve")

    # 2. Apply
    client.post(
        f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/apply",
        json={"confirm_application": True},
    )

    # 3. Rollback
    client.post(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/rollback")

    # 4. Fetch audit log
    audit_res = client.get(f"/api/v1/projects/{test_env['proj_id']}/repair/{proposal.id}/audit-log")
    assert audit_res.status_code == 200
    data = audit_res.json()
    events = [e["event_type"] for e in data["events"]]

    assert "approved" in events
    assert "apply_started" in events
    assert "applied_successfully" in events
    assert "rollback_succeeded" in events
