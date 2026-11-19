import uuid
import pytest


@pytest.fixture
def multi_lang_project(client):
    name = f"AnalysisProj_{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/v1/projects", json={"name": name, "language": "python"})
    assert resp.status_code == 201
    proj_id = resp.json()["id"]

    # 1. Python file
    py_code = """
import os

class Worker:
    def __init__(self, name: str):
        self.name = name

    async def execute(self) -> bool:
        return True
"""
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "worker.py", "content": py_code})

    # 2. JavaScript file
    js_code = """
import { helper } from './helper';

function compute(val) {
    if (val > 0) {
        return val * 2;
    }
    return 0;
}
"""
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "compute.js", "content": js_code})

    # 3. TypeScript file
    ts_code = """
import { BaseConfig } from './types';

export interface Config {
    apiKey: string;
    timeout: number;
}

export class Client {
    public connect(cfg: Config): boolean {
        return true;
    }
}
"""
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "client.ts", "content": ts_code})

    # 4. TSX file
    tsx_code = """
import React from 'react';

export const Banner: React.FC<{ message: string }> = ({ message }) => {
    return <div className="banner">{message}</div>;
};
"""
    client.post(f"/api/v1/projects/{proj_id}/files", json={"path": "Banner.tsx", "content": tsx_code})

    return proj_id


def test_parser_status_endpoint(client, multi_lang_project):
    resp = client.get(f"/api/v1/projects/{multi_lang_project}/analysis/parser-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["readiness"] is True
    assert "Python" in data["supported_languages"]
    assert "JavaScript" in data["supported_languages"]
    assert "TypeScript" in data["supported_languages"]
    assert data["limits"]["max_file_size_bytes"] > 0
    assert "node_modules" in data["limits"]["excluded_directories"]


def test_multi_language_project_analysis(client, multi_lang_project):
    # Trigger full analysis
    parse_resp = client.post(f"/api/v1/projects/{multi_lang_project}/analysis/parse")
    assert parse_resp.status_code == 201
    result = parse_resp.json()

    assert result["status"] == "completed"
    assert result["project_id"] == multi_lang_project
    analysis_id = result["analysis_id"]

    stats = result["statistics"]
    assert stats["supported_files"] == 4
    assert stats["parsed_files"] == 4
    assert stats["failed_files"] == 0
    assert stats["python_files"] == 1
    assert stats["javascript_files"] == 1
    assert stats["typescript_files"] == 2
    assert stats["total_classes"] >= 2
    assert stats["total_functions"] >= 2
    assert stats["total_imports"] >= 4

    # Verify latest analysis retrieval
    latest_resp = client.get(f"/api/v1/projects/{multi_lang_project}/analysis/latest")
    assert latest_resp.status_code == 200
    assert latest_resp.json()["analysis_id"] == analysis_id

    # Verify get by analysis ID
    id_resp = client.get(f"/api/v1/projects/{multi_lang_project}/analysis/parse/{analysis_id}")
    assert id_resp.status_code == 200
    assert id_resp.json()["analysis_id"] == analysis_id

    # Verify list files with filter
    py_files_resp = client.get(f"/api/v1/projects/{multi_lang_project}/analysis/parse/{analysis_id}/files?language=Python")
    assert py_files_resp.status_code == 200
    assert len(py_files_resp.json()) == 1
    assert py_files_resp.json()[0]["file_path"] == "worker.py"

    # Verify get specific file analysis
    file_detail_resp = client.get(f"/api/v1/projects/{multi_lang_project}/analysis/parse/{analysis_id}/files/worker.py")
    assert file_detail_resp.status_code == 200
    f_data = file_detail_resp.json()
    assert f_data["language"] == "Python"
    assert len(f_data["symbols"]) >= 2  # Worker, Worker.__init__, Worker.execute


def test_analysis_with_syntax_error_resilience(client, multi_lang_project):
    # Add a broken file
    client.post(
        f"/api/v1/projects/{multi_lang_project}/files",
        json={"path": "syntax_err.py", "content": "def bad_syntax(:\n    pass"}
    )

    parse_resp = client.post(f"/api/v1/projects/{multi_lang_project}/analysis/parse")
    assert parse_resp.status_code == 201
    result = parse_resp.json()

    # One file had a syntax error, but other files parsed successfully!
    assert result["status"] == "completed_with_diagnostics"
    stats = result["statistics"]
    assert stats["failed_files"] == 1
    assert stats["parsed_files"] >= 4
    assert stats["total_diagnostics"] >= 1

    # Diagnostics endpoint
    analysis_id = result["analysis_id"]
    diag_resp = client.get(f"/api/v1/projects/{multi_lang_project}/analysis/parse/{analysis_id}/diagnostics")
    assert diag_resp.status_code == 200
    diags = diag_resp.json()
    assert len(diags) >= 1
    assert any("syntax_err.py" in d["file_path"] for d in diags)


def test_directory_exclusions(client, multi_lang_project):
    from pathlib import Path
    from app.core.config import settings

    # Manually place a file in excluded node_modules directory in workspace
    ws_dir = settings.get_workspace_dir(multi_lang_project)
    nm_dir = ws_dir / "node_modules"
    nm_dir.mkdir(parents=True, exist_ok=True)
    (nm_dir / "ignored.js").write_text("console.log('ignored');", encoding="utf-8")

    parse_resp = client.post(f"/api/v1/projects/{multi_lang_project}/analysis/parse")
    assert parse_resp.status_code == 201
    result = parse_resp.json()

    # Ensure node_modules/ignored.js was NOT included in analyzed files
    file_paths = [f["file_path"] for f in result["files"]]
    assert not any("node_modules" in p for p in file_paths)


def test_nonexistent_project_analysis_returns_404(client):
    fake_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/projects/{fake_id}/analysis/parse")
    assert resp.status_code == 404
