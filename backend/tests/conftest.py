import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add app to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.core.config import settings
from app.services.gemini_service import gemini_service


@pytest.fixture(autouse=True)
def reset_gemini_service_state():
    """Reset the in-memory state of gemini_service before each test."""
    gemini_service._last_test_result = None
    original_key = settings.GEMINI_API_KEY
    yield
    settings.GEMINI_API_KEY = original_key
    gemini_service._last_test_result = None


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
