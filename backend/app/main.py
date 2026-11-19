from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import logger
from app.db.session import Base, engine
from sqlalchemy import text
import app.models  # ensure all models are registered with Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            cursor = conn.execute(text("PRAGMA table_info(root_cause_analyses)"))
            existing_cols = {row[1] for row in cursor.fetchall()}
            if existing_cols:  # table exists
                new_cols = [
                    ("original_code", "TEXT DEFAULT ''"),
                    ("simple_explanation", "TEXT DEFAULT ''"),
                    ("corrected_code", "TEXT DEFAULT ''"),
                    ("correction_explanation", "TEXT DEFAULT ''"),
                    ("assumptions_json", "TEXT DEFAULT '[]'"),
                    ("fix_status", "VARCHAR(32) DEFAULT 'suggested_not_applied'"),
                ]
                for col_name, col_def in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE root_cause_analyses ADD COLUMN {col_name} {col_def}"))
    except Exception as e:
        logger.warning(f"Schema migration check notice: {e}")

    logger.info("Database schema initialized successfully")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FIXMATE AI — Advanced AI-Powered Bug Detection and Autonomous Code Repair Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS specifically for frontend origins (no wildcard with credentials)
allowed_origins = [
    settings.FRONTEND_ORIGIN,
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
# Remove duplicates while preserving order
allowed_origins = list(dict.fromkeys(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = []
    for err in errors:
        msg = err.get("msg", "Invalid input")
        if msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "")
        loc = err.get("loc", [])
        field = loc[-1] if loc else ""
        if field and field != "body" and not msg.lower().startswith(str(field).lower()):
            messages.append(f"{field}: {msg}")
        else:
            messages.append(msg)

    readable_msg = ". ".join(messages) if messages else "Invalid request data"
    logger.warning(f"Validation error on {request.method} {request.url.path}: {readable_msg}")
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": readable_msg, "errors": errors}),
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "path": request.url.path,
        },
    )
