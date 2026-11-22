import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def detection_project(client: TestClient):
    """Creates a fresh project populated with Python and JavaScript files containing intentional bugs."""
    # 1. Create Project
    res = client.post("/api/v1/projects", json={
        "name": f"Detection Engine Test Project {uuid.uuid4().hex[:6]}",
        "description": "Multi-language static bug detection fixture",
        "language": "python"
    })
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # 2. Add Python file with bugs
    py_content = """import os
import sys

def bad_function(items=[]):
    x = 100 / 0
    return items
    print("unreachable")
"""
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "src/worker.py", "content": py_content})

    # 3. Add JavaScript file with bugs
    js_content = """import { used, unused } from './lib.js';

function compute(val) {
    if (val === NaN) {
        console.log("NaN test");
    }
    const result = eval("1 + 1");
    return result;
}
"""
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "src/app.js", "content": js_content})

    # 4. Add Clean file
    clean_content = """def add(a: int, b: int) -> int:
    return a + b
"""
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "src/math.py", "content": clean_content})

    return proj_id


def test_list_detection_rules(client: TestClient, detection_project: str):
    res = client.get(f"/api/v1/projects/{detection_project}/detection/rules")
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 20  # 10 Python + 10 JS/TS
    rule_ids = [r["rule_id"] for r in rules]
    assert "PY-W001" in rule_ids
    assert "PY-W007" in rule_ids
    assert "JS-W001" in rule_ids
    assert "JS-W006" in rule_ids


def test_run_project_detection_and_latest(client: TestClient, detection_project: str):
    # Run detection
    run_res = client.post(f"/api/v1/projects/{detection_project}/detection/run")
    assert run_res.status_code == 201
    run_data = run_res.json()

    run_id = run_data["run_id"]
    assert run_data["status"] == "completed_with_findings"
    assert run_data["files_scanned"] >= 3
    assert run_data["total_findings"] >= 5
    assert run_data["severity_counts"]["critical"] >= 1  # JS-W006 eval
    assert run_data["severity_counts"]["high"] >= 2     # PY-W001 default arg + PY-W007 div zero

    # Get latest
    latest_res = client.get(f"/api/v1/projects/{detection_project}/detection/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["run_id"] == run_id

    # Get specific run
    detail_res = client.get(f"/api/v1/projects/{detection_project}/detection/runs/{run_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["run_id"] == run_id


def test_get_findings_with_filtering(client: TestClient, detection_project: str):
    # Run detection first
    run_res = client.post(f"/api/v1/projects/{detection_project}/detection/run")
    assert run_res.status_code == 201
    run_id = run_res.json()["run_id"]

    # Filter by severity: critical
    crit_res = client.get(f"/api/v1/projects/{detection_project}/detection/runs/{run_id}/findings?severity=critical")
    assert crit_res.status_code == 200
    crit_findings = crit_res.json()
    assert len(crit_findings) >= 1
    assert all(f["severity"] == "critical" for f in crit_findings)

    # Filter by language: Python
    py_res = client.get(f"/api/v1/projects/{detection_project}/detection/runs/{run_id}/findings?language=Python")
    assert py_res.status_code == 200
    py_findings = py_res.json()
    assert len(py_findings) >= 3
    assert all(f["language"] == "Python" for f in py_findings)

    # Filter by rule: PY-W007 (division by zero)
    div_res = client.get(f"/api/v1/projects/{detection_project}/detection/runs/{run_id}/findings?rule_id=PY-W007")
    assert div_res.status_code == 200
    div_findings = div_res.json()
    assert len(div_findings) == 1
    assert div_findings[0]["rule_id"] == "PY-W007"
    assert "division by zero" in div_findings[0]["message"].lower()

    # Search filter
    search_res = client.get(f"/api/v1/projects/{detection_project}/detection/runs/{run_id}/findings?search=unreachable")
    assert search_res.status_code == 200
    search_findings = search_res.json()
    assert len(search_findings) >= 1


def test_run_file_detection(client: TestClient, detection_project: str):
    # Test on existing file
    file_res = client.post(
        f"/api/v1/projects/{detection_project}/detection/run-file",
        json={"file_path": "src/worker.py"}
    )
    assert file_res.status_code == 200
    findings = file_res.json()
    assert len(findings) >= 2

    # Test on ad-hoc source content
    adhoc_res = client.post(
        f"/api/v1/projects/{detection_project}/detection/run-file",
        json={
            "file_path": "inline.py",
            "content": "a = 10 / 0\n",
            "language": "Python"
        }
    )
    assert adhoc_res.status_code == 200
    adhoc_findings = adhoc_res.json()
    assert len(adhoc_findings) == 1
    assert adhoc_findings[0]["rule_id"] == "PY-W007"


def test_nonexistent_project_detection_returns_404(client: TestClient):
    res = client.get("/api/v1/projects/nonexistent-uuid/detection/rules")
    assert res.status_code == 404

    run_res = client.post("/api/v1/projects/nonexistent-uuid/detection/run")
    assert run_res.status_code == 404
