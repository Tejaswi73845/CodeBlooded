from __future__ import annotations

import importlib.util
import os
import platform

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import DocumentChunk, Evidence, EvidenceEntity, ExtractedContent, TimelineEvent
from app.services.ai_service import ai_service
from app.services.audio_service import audio_available, ffmpeg_binary
from app.services.ocr_service import available_ocr_engines
from app.services.timeline_service import clear_timeline  # noqa: F401  (ensures service imports cleanly)
from app.utils.time import utcnow

router = APIRouter(tags=["System"])


def _storage_ok() -> tuple[bool, str | None]:
    try:
        settings.upload_root.mkdir(parents=True, exist_ok=True)
        probe = settings.upload_root / ".health"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, None
    except OSError as exc:
        return False, str(exc)


@router.get("/health")
def health(db: Session = Depends(get_db)):
    database_ok = True
    database_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        database_ok = False
        database_error = str(exc)

    storage_ok, storage_error = _storage_ok()
    counts = {
        "evidence": int(db.scalar(select(func.count(Evidence.id)).where(Evidence.deleted_at.is_(None))) or 0)
        if database_ok
        else 0,
        "entities": int(
            db.scalar(
                select(func.count(func.distinct(EvidenceEntity.entity_id)))
                .select_from(EvidenceEntity)
                .join(Evidence, Evidence.id == EvidenceEntity.evidence_id)
                .where(Evidence.deleted_at.is_(None))
            )
            or 0
        )
        if database_ok
        else 0,
        "events": int(
            db.scalar(
                select(func.count(TimelineEvent.id))
                .join(Evidence, Evidence.id == TimelineEvent.evidence_id)
                .where(Evidence.deleted_at.is_(None))
            )
            or 0
        )
        if database_ok
        else 0,
        "contents": int(
            db.scalar(
                select(func.count(ExtractedContent.id))
                .join(Evidence, Evidence.id == ExtractedContent.evidence_id)
                .where(Evidence.deleted_at.is_(None))
            )
            or 0
        )
        if database_ok
        else 0,
        "chunks": int(
            db.scalar(
                select(func.count(DocumentChunk.id))
                .join(Evidence, Evidence.id == DocumentChunk.evidence_id)
                .where(Evidence.deleted_at.is_(None))
            )
            or 0
        )
        if database_ok
        else 0,
        "embeddedChunks": int(
            db.scalar(
                select(func.count(DocumentChunk.id))
                .join(Evidence, Evidence.id == DocumentChunk.evidence_id)
                .where(Evidence.deleted_at.is_(None), DocumentChunk.embedding.is_not(None))
            )
            or 0
        )
        if database_ok
        else 0,
    }
    indexed_evidence = (
        int(
            db.scalar(
                select(func.count(func.distinct(DocumentChunk.evidence_id)))
                .join(Evidence, Evidence.id == DocumentChunk.evidence_id)
                .where(Evidence.deleted_at.is_(None))
            )
            or 0
        )
        if database_ok
        else 0
    )
    active_evidence = counts["evidence"] or 0
    rag = {
        "enabled": settings.rag_enabled,
        "configured": ai_service.configured,
        "embeddingModel": settings.gemini_embedding_model,
        "embeddingDimensions": settings.gemini_embedding_dimensions,
        "chunks": counts["chunks"],
        "embeddedChunks": counts["embeddedChunks"],
        "indexedEvidence": indexed_evidence,
        "coverage": round(indexed_evidence / active_evidence, 3) if active_evidence else 0,
    }
    processors = {
        "ocr": {
            "engines": available_ocr_engines(),
            "configured": settings.ocr_engine,
        },
        "whisper": {
            "available": audio_available(),
            "model": settings.whisper_model,
        },
        "ffmpeg": {
            "available": bool(ffmpeg_binary()),
            "path": ffmpeg_binary(),
        },
        "spacy": {
            "available": importlib.util.find_spec("spacy") is not None,
            "model": importlib.util.find_spec("en_core_web_sm") is not None,
        },
        "gemini": {
            "configured": ai_service.configured,
            "model": settings.gemini_model,
        },
        "reportlab": {"available": importlib.util.find_spec("reportlab") is not None},
    }
    status_value = "ok" if database_ok and storage_ok else "degraded"
    return {
        "status": status_value,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": utcnow().isoformat(),
        "python": platform.python_version(),
        "database": {
            "ok": database_ok,
            "engine": settings.database_url.split(":", 1)[0],
            "error": database_error,
        },
        "storage": {
            "ok": storage_ok,
            "root": str(settings.upload_root),
            "writable": os.access(settings.upload_root, os.W_OK),
            "error": storage_error,
        },
        "processors": processors,
        "rag": rag,
        "counts": counts,
    }
