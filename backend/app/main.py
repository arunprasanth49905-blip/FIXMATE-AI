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
            # Phase 5 schema migration check
            cursor = conn.execute(text("PRAGMA table_info(root_cause_analyses)"))
            existing_rca_cols = {row[1] for row in cursor.fetchall()}
            if existing_rca_cols:
                rca_cols = [
                    ("original_code", "TEXT DEFAULT ''"),
                    ("simple_explanation", "TEXT DEFAULT ''"),
                    ("corrected_code", "TEXT DEFAULT ''"),
                    ("correction_explanation", "TEXT DEFAULT ''"),
                    ("assumptions_json", "TEXT DEFAULT '[]'"),
                    ("fix_status", "VARCHAR(32) DEFAULT 'suggested_not_applied'"),
                ]
                for col_name, col_def in rca_cols:
                    if col_name not in existing_rca_cols:
                        conn.execute(text(f"ALTER TABLE root_cause_analyses ADD COLUMN {col_name} {col_def}"))

            # Phase 7 schema migration check for repair_proposals
            cursor_repair = conn.execute(text("PRAGMA table_info(repair_proposals)"))
            existing_repair_cols = {row[1] for row in cursor_repair.fetchall()}
            if existing_repair_cols:
                repair_cols = [
                    ("approval_status", "VARCHAR(32) DEFAULT 'pending'"),
                    ("approved_at", "DATETIME"),
                    ("rejected_at", "DATETIME"),
                    ("applied_at", "DATETIME"),
                    ("rollback_at", "DATETIME"),
                    ("rollback_status", "VARCHAR(32)"),
                    ("backup_id", "VARCHAR(36)"),
                    ("backup_path", "VARCHAR(512)"),
                    ("pre_apply_fingerprint", "VARCHAR(64)"),
                    ("post_apply_fingerprint", "VARCHAR(64)"),
                    ("apply_attempt_id", "VARCHAR(36)"),
                    ("apply_error", "TEXT"),
                    ("post_validation_details_json", "TEXT"),
                ]
                for col_name, col_def in repair_cols:
                    if col_name not in existing_repair_cols:
                        conn.execute(text(f"ALTER TABLE repair_proposals ADD COLUMN {col_name} {col_def}"))

            # Project duplicate name protection migration check
            cursor_proj = conn.execute(text("PRAGMA table_info(projects)"))
            existing_proj_cols = {row[1] for row in cursor_proj.fetchall()}
            if existing_proj_cols and "normalized_name" not in existing_proj_cols:
                conn.execute(text("ALTER TABLE projects ADD COLUMN normalized_name VARCHAR(120)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_normalized_name ON projects (normalized_name)"))

            # Backfill any missing normalized_name values
            conn.execute(text("UPDATE projects SET normalized_name = LOWER(TRIM(name)) WHERE normalized_name IS NULL"))

            # Audit and report any existing duplicate project names safely
            dup_cursor = conn.execute(text(
                "SELECT normalized_name, COUNT(*) as cnt, GROUP_CONCAT(id) as ids, "
                "GROUP_CONCAT(name) as names, GROUP_CONCAT(language) as langs "
                "FROM projects GROUP BY normalized_name HAVING COUNT(*) > 1"
            ))
            dup_rows = dup_cursor.fetchall()
            if dup_rows:
                logger.warning(f"Project Name Duplicate Audit: Found {len(dup_rows)} duplicate groups in existing database:")
                for row in dup_rows:
                    logger.warning(
                        f" - Group '{row[0]}': {row[1]} projects. IDs: [{row[2]}], Names: [{row[3]}], Languages: [{row[4]}]"
                    )
            else:
                logger.info("Project Name Duplicate Audit: Zero duplicates detected in existing database.")
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
