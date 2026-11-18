def test_system_info_endpoint_data(client):
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200

    data = response.json()
    assert data["application_name"] == "FIXMATE AI"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
    assert data["api_prefix"] == "/api/v1"
    assert "Python" in data["supported_languages"]
    assert "JavaScript" in data["supported_languages"]
    assert data["configured_ai_provider"] == "Google Gemini"
    assert data["backend_status"] == "running"
