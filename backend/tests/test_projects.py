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


def test_reject_exact_duplicate_name(client):
    base_name = f"Duplicate_Test_{uuid.uuid4().hex[:6]}"
    # 1. First creation succeeds
    resp1 = client.post("/api/v1/projects", json={"name": base_name, "language": "python"})
    assert resp1.status_code == 201

    # 2. Second creation with exact same name is rejected
    resp2 = client.post("/api/v1/projects", json={"name": base_name, "language": "python"})
    assert resp2.status_code == 409
    data = resp2.json()
    assert "already exists" in data["detail"].lower()


def test_reject_case_insensitive_duplicate(client):
    tag = uuid.uuid4().hex[:6]
    original = f"Phase4_Bug_Detection_{tag}"
    lowercase = f"phase4_bug_detection_{tag}"
    uppercase = f"PHASE4_BUG_DETECTION_{tag}"

    # 1. Create original
    resp1 = client.post("/api/v1/projects", json={"name": original, "language": "python"})
    assert resp1.status_code == 201

    # 2. Attempt lowercase variant
    resp2 = client.post("/api/v1/projects", json={"name": lowercase, "language": "python"})
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()

    # 3. Attempt uppercase variant
    resp3 = client.post("/api/v1/projects", json={"name": uppercase, "language": "python"})
    assert resp3.status_code == 409


def test_reject_whitespace_padded_duplicate(client):
    tag = uuid.uuid4().hex[:6]
    clean_name = f"Whitespace_Proj_{tag}"
    padded_name = f"   Whitespace_Proj_{tag}   "

    # 1. Create clean
    resp1 = client.post("/api/v1/projects", json={"name": clean_name, "language": "python"})
    assert resp1.status_code == 201

    # 2. Attempt padded duplicate
    resp2 = client.post("/api/v1/projects", json={"name": padded_name, "language": "python"})
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_reject_duplicate_across_different_languages(client):
    tag = uuid.uuid4().hex[:6]
    base_name = f"Cross_Lang_{tag}"

    # 1. Create as Python
    resp1 = client.post("/api/v1/projects", json={"name": base_name, "language": "python"})
    assert resp1.status_code == 201

    # 2. Attempt same name as JavaScript
    resp2 = client.post("/api/v1/projects", json={"name": base_name, "language": "javascript"})
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()

    # 3. Attempt same name as General
    resp3 = client.post("/api/v1/projects", json={"name": base_name, "language": "general"})
    assert resp3.status_code == 409


def test_reject_empty_and_whitespace_only_names(client):
    resp_empty = client.post("/api/v1/projects", json={"name": ""})
    assert resp_empty.status_code == 422

    resp_spaces = client.post("/api/v1/projects", json={"name": "     "})
    assert resp_spaces.status_code == 422


def test_reject_duplicate_rename(client):
    tag = uuid.uuid4().hex[:6]
    name_a = f"Project_Alpha_{tag}"
    name_b = f"Project_Beta_{tag}"

    resp_a = client.post("/api/v1/projects", json={"name": name_a})
    assert resp_a.status_code == 201

    resp_b = client.post("/api/v1/projects", json={"name": name_b})
    assert resp_b.status_code == 201
    proj_b_id = resp_b.json()["id"]

    # Attempt to rename B to A
    rename_resp = client.patch(f"/api/v1/projects/{proj_b_id}", json={"name": name_a})
    assert rename_resp.status_code == 409
    assert "already exists" in rename_resp.json()["detail"].lower()

    # Attempt case-insensitive rename to A
    rename_resp2 = client.patch(f"/api/v1/projects/{proj_b_id}", json={"name": name_a.lower()})
    assert rename_resp2.status_code == 409


def test_allow_rename_with_same_name(client):
    tag = uuid.uuid4().hex[:6]
    name = f"Stable_Name_{tag}"

    create_resp = client.post("/api/v1/projects", json={"name": name, "description": "Original"})
    assert create_resp.status_code == 201
    proj_id = create_resp.json()["id"]

    # Update description only
    update_resp = client.patch(f"/api/v1/projects/{proj_id}", json={"description": "Updated desc"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == name

    # Update keeping the exact same name
    update_resp2 = client.patch(f"/api/v1/projects/{proj_id}", json={"name": name, "language": "javascript"})
    assert update_resp2.status_code == 200
    assert update_resp2.json()["language"] == "javascript"


def test_concurrent_duplicate_creation_protection(client):
    import concurrent.futures

    tag = uuid.uuid4().hex[:6]
    name = f"Race_Condition_Proj_{tag}"

    def try_create():
        return client.post("/api/v1/projects", json={"name": name, "language": "python"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(try_create) for _ in range(5)]
        results = [f.result() for f in futures]

    statuses = [r.status_code for r in results]
    # Exactly one request must succeed (201), the rest must be rejected (409)
    assert statuses.count(201) == 1
    assert statuses.count(409) == 4


def test_existing_duplicate_projects_remain_accessible(client):
    """
    Ensures that if duplicate projects exist in database (e.g. legacy records),
    both remain accessible and functional without errors or deletion.
    """
    from app.db.session import SessionLocal
    from app.models.project import Project

    tag = uuid.uuid4().hex[:6]
    dup_name = f"Legacy_Duplicate_{tag}"
    p1_id = f"legacy-dup-1-{tag}"
    p2_id = f"legacy-dup-2-{tag}"

    db = SessionLocal()
    try:
        p1 = Project(id=p1_id, name=dup_name, language="python", description="First duplicate")
        p2 = Project(id=p2_id, name=dup_name, language="javascript", description="Second duplicate")
        db.add_all([p1, p2])
        db.commit()
    finally:
        db.close()

    # Both projects must be accessible via API
    resp1 = client.get(f"/api/v1/projects/{p1_id}")
    assert resp1.status_code == 200
    assert resp1.json()["id"] == p1_id
    assert resp1.json()["language"] == "python"
    assert resp1.json()["is_duplicate"] is True

    resp2 = client.get(f"/api/v1/projects/{p2_id}")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == p2_id
    assert resp2.json()["language"] == "javascript"
    assert resp2.json()["is_duplicate"] is True


def test_existing_projects_and_files_not_deleted_or_merged(client):
    """
    Ensures that files created in two projects remain completely isolated and never merged.
    """
    tag = uuid.uuid4().hex[:6]
    name1 = f"Project_Isolated_1_{tag}"
    name2 = f"Project_Isolated_2_{tag}"

    r1 = client.post("/api/v1/projects", json={"name": name1})
    p1_id = r1.json()["id"]

    r2 = client.post("/api/v1/projects", json={"name": name2})
    p2_id = r2.json()["id"]

    client.post(f"/api/v1/projects/{p1_id}/files", json={"path": "file1.py", "content": "x = 1"})
    client.post(f"/api/v1/projects/{p2_id}/files", json={"path": "file2.py", "content": "y = 2"})

    f1 = client.get(f"/api/v1/projects/{p1_id}/files").json()
    f2 = client.get(f"/api/v1/projects/{p2_id}/files").json()

    assert any(item["name"] == "file1.py" for item in f1)
    assert not any(item["name"] == "file2.py" for item in f1)

    assert any(item["name"] == "file2.py" for item in f2)
    assert not any(item["name"] == "file1.py" for item in f2)


def test_duplicate_audit_endpoint(client):
    resp = client.get("/api/v1/projects/duplicates/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_duplicate_groups" in data
    assert "total_duplicate_projects" in data
    assert "groups" in data
