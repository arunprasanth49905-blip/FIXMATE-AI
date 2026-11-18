from fastapi import APIRouter

from app.core.config import settings
from app.schemas.ai import AIStatusResponse, AITestResponse
from app.schemas.system import SystemInfoResponse
from app.services.gemini_service import gemini_service

router = APIRouter()


@router.get("/system/info", response_model=SystemInfoResponse, tags=["System"])
def get_system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        application_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        api_prefix=settings.API_V1_PREFIX,
        supported_languages=settings.SUPPORTED_LANGUAGES,
        configured_ai_provider="Google Gemini",
        backend_status="running",
    )


@router.get("/system/ai-status", response_model=AIStatusResponse, tags=["System", "AI"])
def get_ai_status() -> AIStatusResponse:
    return gemini_service.get_status()


@router.post("/system/ai-test", response_model=AITestResponse, tags=["System", "AI"])
def test_ai_connection() -> AITestResponse:
    return gemini_service.test_connection()
