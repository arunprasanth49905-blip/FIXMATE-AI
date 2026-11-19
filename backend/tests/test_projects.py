import uuid


def test_create_project(client):
    unique_name = f"Test Project {uuid.uuid4().hex[:6]}"
    payload = {
        "name": unique_name,
        "description": "A test repository for unit tests",
        "language": "python",
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == unique_name
    assert data["description"] == "A test repository for unit tests"
    assert data["language"] == "python"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["file_count"] == 0


def test_list_and_search_projects(client):
    name_alpha = f"Alpha_{uuid.uuid4().hex[:6]}"
    name_beta = f"Beta_{uuid.uuid4().hex[:6]}"

    client.post("/api/v1/projects", json={"name": name_alpha, "language": "python"})
    client.post("/api/v1/projects", json={"name": name_beta, "language": "javascript"})

    # List all
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    all_projects = response.json()["projects"]
    assert len(all_projects) >= 2

    # Search specifically for Alpha
    search_resp = client.get(f"/api/v1/projects?search={name_alpha}")
    assert search_resp.status_code == 200
    search_data = search_resp.json()["projects"]
    assert any(p["name"] == name_alpha for p in search_data)
    assert not any(p["name"] == name_beta for p in search_data)


def test_get_project_by_id(client):
    name = f"GetTest_{uuid.uuid4().hex[:6]}"
    create_resp = client.post("/api/v1/projects", json={"name": name, "language": "typescript"})
    proj_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/projects/{proj_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == proj_id
    assert data["name"] == name
    assert data["language"] == "typescript"

    # Non-existent project
    not_found_resp = client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert not_found_resp.status_code == 404


def test_update_project(client):
    name = f"OldName_{uuid.uuid4().hex[:6]}"
    create_resp = client.post("/api/v1/projects", json={"name": name, "language": "python"})
    proj_id = create_resp.json()["id"]

    new_name = f"Renamed_{uuid.uuid4().hex[:6]}"
    update_resp = client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"name": new_name, "description": "Updated desc"}
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["name"] == new_name
    assert updated_data["description"] == "Updated desc"


def test_delete_project(client):
    name = f"ToDelete_{uuid.uuid4().hex[:6]}"
    create_resp = client.post("/api/v1/projects", json={"name": name})
    proj_id = create_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == 204

    # Verify not found
    get_resp = client.get(f"/api/v1/projects/{proj_id}")
    assert get_resp.status_code == 404


def test_project_name_validation(client):
    # Empty name should fail validation
    resp = client.post("/api/v1/projects", json={"name": "   "})
    assert resp.status_code == 422
