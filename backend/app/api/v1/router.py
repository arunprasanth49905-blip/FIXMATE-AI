from fastapi import APIRouter

from app.api.v1.endpoints import health, system, projects, files, parsing

api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(system.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(files.router)
api_v1_router.include_router(parsing.router)
