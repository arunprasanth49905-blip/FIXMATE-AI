from unittest.mock import MagicMock, patch
from app.core.config import settings


def test_ai_status_missing_api_key(client):
    """3. AI status handles missing API key."""
    settings.GEMINI_API_KEY = None

    response = client.get("/api/v1/system/ai-status")
    assert response.status_code == 200

    data = response.json()
    assert data["provider"] == "Google Gemini"
    assert data["configured"] is False
    assert data["connection_state"] == "not_configured"
    assert "not configured" in data["message"].lower()


def test_ai_status_configured_api_key(client):
    """4. AI status handles configured API key (untested initial state)."""
    settings.GEMINI_API_KEY = "test-mock-api-key"

    response = client.get("/api/v1/system/ai-status")
    assert response.status_code == 200

    data = response.json()
    assert data["provider"] == "Google Gemini"
    assert data["configured"] is True
    assert data["connection_state"] == "configured_untested"
    assert "not been verified" in data["message"].lower()


def test_ai_test_missing_credentials(client):
    """5. AI test handles missing credentials."""
    settings.GEMINI_API_KEY = ""

    response = client.post("/api/v1/system/ai-test")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is False
    assert data["error"] == "API_KEY_NOT_CONFIGURED"
    assert "not configured" in data["message"].lower()


def test_ai_test_success_mocked_provider(client):
    """6. AI test success using mocked provider."""
    settings.GEMINI_API_KEY = "mock-valid-api-key"

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "PONG"
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        response = client.post("/api/v1/system/ai-test")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["provider"] == "Google Gemini"
        assert data["latency_ms"] is not None
        assert data["error"] is None
        assert "successful" in data["message"].lower()

    # Verify that get_ai_status now reflects connected state
    status_resp = client.get("/api/v1/system/ai-status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["configured"] is True
    assert status_data["connection_state"] == "connected"


def test_ai_test_failure_handling(client):
    """7. AI test failure handling."""
    settings.GEMINI_API_KEY = "mock-invalid-api-key"

    with patch("google.genai.Client", side_effect=Exception("API_KEY_INVALID: 403 Forbidden")):
        response = client.post("/api/v1/system/ai-test")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["error"] == "AUTHENTICATION_ERROR"
        assert "invalid" in data["message"].lower() or "unauthorized" in data["message"].lower()

    # Verify that get_ai_status reflects connection_failed state
    status_resp = client.get("/api/v1/system/ai-status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["connection_state"] == "connection_failed"


def test_secrets_not_exposed_in_responses(client):
    """8. Secrets are not exposed in responses."""
    secret_key = "AIzaSyD-SecretKey1234567890abcdef"
    settings.GEMINI_API_KEY = secret_key

    # Test status endpoint
    status_resp = client.get("/api/v1/system/ai-status")
    assert secret_key not in status_resp.text

    # Test error output redaction
    with patch("google.genai.Client", side_effect=Exception(f"Failed with key={secret_key}")):
        test_resp = client.post("/api/v1/system/ai-test")
        assert secret_key not in test_resp.text
        assert "[REDACTED]" in test_resp.text or "connection failed" in test_resp.text.lower()
