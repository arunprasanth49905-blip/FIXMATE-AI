import io
import uuid
import pytest
from app.core.config import settings


@pytest.fixture
def test_project(client):
    name = f"FileProj_{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/v1/projects", json={"name": name, "language": "python"})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_file_and_read(client, test_project):
    payload = {
        "path": "src/main.py",
        "content": "def hello():\n    return 'world'\n",
        "is_directory": False,
    }
    create_resp = client.post(f"/api/v1/projects/{test_project}/files", json=payload)
    assert create_resp.status_code == 201
    file_id = create_resp.json()["id"]
    assert create_resp.json()["path"] == "src/main.py"
    assert create_resp.json()["name"] == "main.py"
    assert create_resp.json()["extension"] == ".py"

    # Read content
    read_resp = client.get(f"/api/v1/projects/{test_project}/files/{file_id}")
    assert read_resp.status_code == 200
    data = read_resp.json()
    assert data["content"] == "def hello():\n    return 'world'\n"
    assert data["is_binary"] is False
    assert data["size"] > 0


def test_create_directory_and_tree(client, test_project):
    # Create directory
    dir_resp = client.post(
        f"/api/v1/projects/{test_project}/files",
        json={"path": "tests", "is_directory": True}
    )
    assert dir_resp.status_code == 201
    assert dir_resp.json()["is_directory"] is True

    # Create file inside directory
    file_resp = client.post(
        f"/api/v1/projects/{test_project}/files",
        json={"path": "tests/test_basic.py", "content": "assert True\n", "is_directory": False}
    )
    assert file_resp.status_code == 201

    # Request tree structure
    tree_resp = client.get(f"/api/v1/projects/{test_project}/files?tree=true")
    assert tree_resp.status_code == 200
    tree = tree_resp.json()
    assert isinstance(tree, list)
    tests_folder = next((item for item in tree if item["name"] == "tests" and item["is_directory"]), None)
    assert tests_folder is not None
    assert tests_folder["children"] is not None
    assert any(c["name"] == "test_basic.py" for c in tests_folder["children"])


def test_save_file_content(client, test_project):
    create_resp = client.post(
        f"/api/v1/projects/{test_project}/files",
        json={"path": "app.py", "content": "x = 1"}
    )
    file_id = create_resp.json()["id"]

    new_content = "x = 42\ny = 100\nprint(x + y)"
    save_resp = client.put(
        f"/api/v1/projects/{test_project}/files/{file_id}",
        json={"content": new_content}
    )
    assert save_resp.status_code == 200

    # Verify content updated
    read_resp = client.get(f"/api/v1/projects/{test_project}/files/{file_id}")
    assert read_resp.json()["content"] == new_content


def test_rename_file(client, test_project):
    create_resp = client.post(
        f"/api/v1/projects/{test_project}/files",
        json={"path": "old_name.py", "content": "# comment"}
    )
    file_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/projects/{test_project}/files/{file_id}",
        json={"path": "new_name.py"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["path"] == "new_name.py"
    assert patch_resp.json()["name"] == "new_name.py"


def test_delete_file(client, test_project):
    create_resp = client.post(
        f"/api/v1/projects/{test_project}/files",
        json={"path": "temp.txt", "content": "temp"}
    )
    file_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/projects/{test_project}/files/{file_id}")
    assert del_resp.status_code == 204

    # Verify 404
    get_resp = client.get(f"/api/v1/projects/{test_project}/files/{file_id}")
    assert get_resp.status_code == 404


def test_invalid_file_extension(client, test_project):
    # .exe is not allowed
    resp = client.post(
        f"/api/v1/projects/{test_project}/files",
        json={"path": "malicious.exe", "content": "dummy"}
    )
    assert resp.status_code == 400
    assert "not supported" in resp.json()["detail"].lower()


def test_path_traversal_attempts_prevented(client, test_project):
    traversal_paths = [
        "../outside.py",
        "../../etc/passwd",
        "folder/../../outside.py",
        "..\\windows\\system32",
        "/absolute/path.py",
        "C:\\autoexec.bat",
    ]

    for p in traversal_paths:
        resp = client.post(
            f"/api/v1/projects/{test_project}/files",
            json={"path": p, "content": "evil"}
        )
        assert resp.status_code in [400, 422, 403], f"Path traversal not caught for: {p}"


def test_file_upload(client, test_project):
    file_content = b"print('Uploaded from client')\n"
    file_tuple = ("script.py", io.BytesIO(file_content), "text/x-python")

    response = client.post(
        f"/api/v1/projects/{test_project}/upload",
        files={"files": file_tuple},
        data={"paths": "scripts/uploaded.py"},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["uploaded"]) == 1
    assert data["uploaded"][0]["name"] == "uploaded.py"
    assert data["uploaded"][0]["path"] == "scripts/uploaded.py"
    assert len(data["errors"]) == 0


def test_oversized_upload_handling(client, test_project):
    # Create content larger than max upload limit
    original_limit = settings.MAX_UPLOAD_SIZE_BYTES
    try:
        settings.MAX_UPLOAD_SIZE_BYTES = 50  # 50 bytes for test
        oversized = "a" * 100
        resp = client.post(
            f"/api/v1/projects/{test_project}/files",
            json={"path": "big.txt", "content": oversized}
        )
        assert resp.status_code == 413
        assert "exceeds maximum allowed size" in resp.json()["detail"].lower()
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = original_limit
