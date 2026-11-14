from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError
from app.models import Evidence
from app.models.enums import AuditResult, EvidenceStatus, ProcessingStage
from app.schemas.evidence import (
    DuplicateWarning,
    EvidenceDetail,
    EvidencePage,
    StatusResponse,
    UploadError,
    UploadResponse,
)
from app.services import evidence_service, file_service
from app.services.audit_service import record_audit
from app.services.integrity_service import verify_evidence_integrity
from app.services.pipeline_service import process_evidence
from app.utils.http import actor_name, client_ip, optional_uuid, user_agent
from app.utils.logging import get_logger

router = APIRouter(prefix="/evidence", tags=["Evidence"])
logger = get_logger(__name__)


def _counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Evidence.status, func.count(Evidence.id))
        .where(Evidence.deleted_at.is_(None))
        .group_by(Evidence.status)
    ).all()
    counts = {value.value: 0 for value in EvidenceStatus}
    counts.update({status_value.value: int(total) for status_value, total in rows})
    return counts


def _capture_metadata(
    *,
    captured_date: str | None,
    captured_time: str | None,
    location: str | None,
    persons: str | None,
    note: str | None,
) -> dict:
    """Normalise the optional upload-time capture details supplied with a file."""
    occurred_at: str | None = None
    if captured_date and captured_date.strip():
        candidate = f"{captured_date.strip()}T{(captured_time or '00:00').strip() or '00:00'}"
        try:
            occurred_at = datetime.fromisoformat(candidate).isoformat()
        except ValueError:
            occurred_at = None
    person_names: list[str] = []
    if persons and persons.strip():
        text = persons.strip()
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            person_names = [str(item).strip() for item in parsed if str(item).strip()]
        elif isinstance(parsed, str):
            person_names = [parsed.strip()] if parsed.strip() else []
        else:
            person_names = [part.strip() for part in text.split(",") if part.strip()]
    return {
        "occurredAt": occurred_at,
        "location": (location or "").strip() or None,
        "persons": person_names[:20],
        "note": (note or "").strip() or None,
    }


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_evidence(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(default=[]),
    file: UploadFile | None = File(default=None),
    captured_date: str | None = Form(default=None, alias="date", max_length=32),
    captured_time: str | None = Form(default=None, alias="time", max_length=32),
    location: str | None = Form(default=None, max_length=300),
    persons: str | None = Form(default=None, max_length=1000),
    note: str | None = Form(default=None, max_length=2000),
    auto_detect: str | None = Form(default=None, alias="autoDetect", max_length=16),
    db: Session = Depends(get_db),
):
    uploads = [*files]
    if file is not None:
        uploads.append(file)
    if not uploads:
        raise AppError(400, "no_files", "Attach at least one file using the `files` field.")
    if len(uploads) > 20:
        raise AppError(400, "too_many_files", "A maximum of 20 files can be uploaded at once.")

    actor = actor_name(request)
    user = file_service.get_or_create_default_user(db, actor)
    capture = _capture_metadata(
        captured_date=captured_date,
        captured_time=captured_time,
        location=location,
        persons=persons,
        note=note,
    )
    detect_missing = (auto_detect or "").strip().lower() in {"1", "true", "on", "yes"}
    items = []
    duplicates: list[DuplicateWarning] = []
    errors: list[UploadError] = []

    for upload in uploads:
        filename = upload.filename or "evidence"
        try:
            stored = await file_service.store_upload(
                db, upload, user, capture=capture, auto_detect=detect_missing
            )
        except AppError as exc:
            errors.append(UploadError(filename=filename, error=exc.message))
            record_audit(
                db,
                actor=actor,
                action="Upload rejected",
                target_type="evidence",
                result=AuditResult.WARNING,
                details={"filename": filename, "error": exc.message},
                ip_address=client_ip(request),
                user_agent=user_agent(request),
            )
            continue
        except Exception:  # noqa: BLE001 - per-file isolation
            logger.exception("Upload failed for %s", filename)
            errors.append(UploadError(filename=filename, error="The file could not be preserved."))
            continue

        items.append(evidence_service.serialize_evidence(db, stored.evidence))
        for hit in stored.duplicates:
            duplicates.append(
                DuplicateWarning(
                    evidence_id=hit.evidence.id,
                    reference=hit.evidence.reference,
                    name=hit.evidence.original_filename,
                    sha256=hit.evidence.sha256,
                    similarity=hit.similarity,
                    kind=hit.kind,
                )
            )
        background_tasks.add_task(process_evidence, str(stored.evidence.id))

    if not items:
        raise AppError(400, "upload_failed", "No files could be preserved.", [e.model_dump(by_alias=True) for e in errors])

    return UploadResponse(items=items, duplicates=duplicates, errors=errors, accepted=len(items))


@router.get("", response_model=EvidencePage)
def list_evidence(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=300),
    file_type: str | None = Query(default=None, alias="type"),
    status_filter: str | None = Query(default=None, alias="status"),
    entity_id: str | None = Query(default=None, alias="entityId"),
    person_id: str | None = Query(default=None, alias="personId"),
    duplicate_only: bool = Query(default=False, alias="duplicates"),
    sort: str = Query(default="newest", pattern="^(newest|oldest|name|size)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items, total = evidence_service.list_evidence(
        db,
        q=q,
        file_type=file_type,
        status=status_filter,
        entity_id=optional_uuid(entity_id or person_id, "personId"),
        duplicate_only=duplicate_only,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return EvidencePage(items=items, total=total, limit=limit, offset=offset, counts=_counts(db))


@router.get("/{evidence_id}", response_model=EvidenceDetail)
def get_evidence(evidence_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    evidence = file_service.get_active_evidence(db, evidence_id)
    detail = evidence_service.get_detail(db, evidence)
    record_audit(
        db,
        actor=actor_name(request),
        action="Evidence viewed",
        target_type="evidence",
        target_id=str(evidence.id),
        details={"filename": evidence.original_filename, "reference": evidence.reference},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
    )
    return detail


@router.get("/{evidence_id}/status", response_model=StatusResponse)
def get_status(evidence_id: uuid.UUID, db: Session = Depends(get_db)):
    evidence = file_service.get_active_evidence(db, evidence_id)
    return StatusResponse(
        id=evidence.id,
        status=evidence.status.value,
        stage=evidence.processing_stage.value,
        progress=evidence.processing_progress,
        error=evidence.error_message,
        processing_started_at=evidence.processing_started_at,
        processing_completed_at=evidence.processing_completed_at,
        integrity=evidence.integrity_status.value,
        verified_at=evidence.last_verified_at,
    )


@router.get("/{evidence_id}/download")
def download_evidence(evidence_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    evidence = file_service.get_active_evidence(db, evidence_id)
    path = file_service.resolve_original(evidence)
    record_audit(
        db,
        actor=actor_name(request),
        action="Evidence downloaded",
        target_type="evidence",
        target_id=str(evidence.id),
        details={"filename": evidence.original_filename, "sha256": evidence.sha256},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
    )
    return FileResponse(
        path,
        media_type=evidence.mime_type,
        filename=evidence.original_filename,
        headers={"X-Evidence-SHA256": evidence.sha256, "Cache-Control": "private, no-store"},
    )


@router.post("/{evidence_id}/verify")
def verify_evidence(evidence_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    evidence = file_service.get_active_evidence(db, evidence_id)
    integrity = verify_evidence_integrity(
        db,
        evidence,
        actor=actor_name(request),
        ip_address=client_ip(request),
        user_agent=user_agent(request),
    )
    return {
        "id": str(evidence.id),
        "integrity": integrity.value,
        "sha256": evidence.sha256,
        "verifiedAt": evidence.last_verified_at,
    }


@router.post("/{evidence_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
def reprocess_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    evidence = file_service.get_active_evidence(db, evidence_id)
    if evidence.status == EvidenceStatus.PROCESSING:
        raise AppError(409, "already_processing", "This item is already being processed.")
    evidence.status = EvidenceStatus.PENDING
    evidence.processing_stage = ProcessingStage.QUEUED
    evidence.processing_progress = 0
    evidence.error_message = None
    db.add(evidence)
    db.commit()
    record_audit(
        db,
        actor=actor_name(request),
        action="Reprocessing requested",
        target_type="evidence",
        target_id=str(evidence.id),
        details={"filename": evidence.original_filename},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
    )
    background_tasks.add_task(process_evidence, str(evidence.id))
    return {"id": str(evidence.id), "status": "pending"}


@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    evidence = file_service.get_active_evidence(db, evidence_id)
    file_service.soft_delete(db, evidence, actor=actor_name(request), ip=client_ip(request))
    return {"id": str(evidence_id), "deleted": True, "originalRetained": True}
