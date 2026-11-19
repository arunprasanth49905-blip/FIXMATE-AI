from typing import List, Optional
from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    application_name: str
    version: str
    environment: str
    api_prefix: str
    supported_languages: List[str]
    configured_ai_provider: str
    backend_status: str
    total_projects: Optional[int] = 0
