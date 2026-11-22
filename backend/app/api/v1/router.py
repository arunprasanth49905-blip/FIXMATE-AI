from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    system,
    projects,
    files,
    parsing,
    detection,
    root_cause,
    repair,
    verification,
    sandbox,
)

api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(system.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(files.router)
api_v1_router.include_router(parsing.router)
api_v1_router.include_router(detection.router)
api_v1_router.include_router(root_cause.router)
api_v1_router.include_router(repair.router)
api_v1_router.include_router(verification.router)
api_v1_router.include_router(sandbox.router)
