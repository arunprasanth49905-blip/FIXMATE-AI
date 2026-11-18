from typing import Optional
from pydantic import BaseModel


class AIStatusResponse(BaseModel):
    provider: str
    configured: bool
    configured_model: str
    connection_state: str  # "not_configured" | "configured_untested" | "connected" | "connection_failed"
    message: str


class AITestResponse(BaseModel):
    success: bool
    provider: str
    model: str
    latency_ms: Optional[float] = None
    message: str
    timestamp: str
    error: Optional[str] = None
