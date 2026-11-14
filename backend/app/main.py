from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal, init_db
from app.errors import AppError
from app.middleware.request_context import RequestContextMiddleware
from app.models import Evidence
from app.models.enums import EvidenceStatus, ProcessingStage
from app.routers import assistant, audit, entities, evidence, health, reports, timeline
from app.services.ai_service import ai_service
from app.services.audio_service import ensure_ffmpeg_on_path
from app.services.audit_service import record_audit
from app.services.file_service import get_or_create_default_user
from app.services.ocr_service import available_ocr_engines
from app.utils.logging import configure_logging, get_logger
from app.utils.time import utcnow

logger = get_logger(__name__)


def _recover_interrupted_jobs() -> None:
    db = SessionLocal()
    try:
        result = db.execute(
            update(Evidence)
            .where(Evidence.status == EvidenceStatus.PROCESSING)
            .values(
                status=EvidenceStatus.FAILED,
                processing_stage=ProcessingStage.FAILED,
                error_message="Processing was interrupted by a service restart. Use reprocess to retry.",
                processing_completed_at=utcnow(),
            )
        )
        db.commit()
        if result.rowcount:
            logger.warning("Marked %s interrupted jobs as failed", result.rowcount)
            record_audit(
                db,
                actor="System",
                action="Interrupted jobs recovered",
                target_type="system",
                details={"count": result.rowcount},
            )
        get_or_create_default_user(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    ensure_ffmpeg_on_path()
    settings.upload_root.mkdir(parents=True, exist_ok=True)
    (settings.upload_root / "originals").mkdir(exist_ok=True)
    (settings.upload_root / "derived").mkdir(exist_ok=True)
    (settings.upload_root / "tmp").mkdir(exist_ok=True)
    if settings.auto_create_tables:
        init_db()
    _recover_interrupted_jobs()
    logger.info("TraceVault %s starting (%s)", settings.app_version, settings.environment)
    logger.info("Uploads: %s", settings.upload_root)
    logger.info("Database: %s", settings.database_url.split("@")[-1])
    if not ai_service.configured:
        key_name = "OPENCODE_API_KEY" if settings.ai_provider == "opencode" else "GEMINI_API_KEY"
        logger.warning("%s is not set — AI synthesis uses deterministic extraction fallbacks.", key_name)
    if not any(available_ocr_engines().values()):
        logger.warning("No OCR engine is available. Install EasyOCR or configure Gemini vision.")
    yield
    logger.info("TraceVault shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TraceVault — Evidence Intelligence API",
        description=(
            "Evidence preservation, multimodal extraction, entity resolution, timeline reconstruction "
            "and evidence-backed investigation assistance. Original files are immutable; every access "
            "is recorded in a chained audit ledger."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "TraceVault", "url": "https://example.invalid"},
        openapi_tags=[
            {"name": "Evidence", "description": "Upload, search, preview and download preserved evidence."},
            {"name": "Timeline", "description": "Reconstructed chronology and filters."},
            {"name": "Entities", "description": "People, phones, emails, organizations and the relationship graph."},
            {"name": "Assistant", "description": "Evidence-grounded Q&A with source citations."},
            {"name": "Reports", "description": "Structured investigation reports and PDF export."},
            {"name": "Audit", "description": "Tamper-evident access and processing ledger."},
            {"name": "System", "description": "Health and capability discovery."},
        ],
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Evidence-SHA256", "Content-Disposition"],
        max_age=86400,
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": jsonable_encoder(exc.details),
                    "requestId": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "The request payload is invalid.",
                    "details": jsonable_encoder(exc.errors()),
                    "requestId": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred. The request ID is in the logs.",
                    "details": None,
                    "requestId": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.get("/", tags=["System"])
    def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": f"{settings.api_prefix}/health",
        }

    @app.get("/health", tags=["System"], include_in_schema=False)
    def health_alias(request: Request):
        # Convenience alias used by container health checks.
        forwarded = request.url.replace(path=f"{settings.api_prefix}/health")
        from starlette.responses import RedirectResponse

        return RedirectResponse(url=str(forwarded), status_code=307)

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(evidence.router, prefix=settings.api_prefix)
    app.include_router(timeline.router, prefix=settings.api_prefix)
    app.include_router(entities.router, prefix=settings.api_prefix)
    app.include_router(assistant.router, prefix=settings.api_prefix)
    app.include_router(reports.router, prefix=settings.api_prefix)
    app.include_router(audit.router, prefix=settings.api_prefix)

    return app


app = create_app()
