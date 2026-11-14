from __future__ import annotations

import hashlib
import os
import shutil
import stat
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import FileTooLargeError, NotFoundError, UnsupportedMediaError
from app.models import Evidence, User
from app.models.enums import EvidenceStatus, IntegrityStatus, ProcessingStage
from app.services.audit_service import record_audit
from app.utils.files import (
    detect_file_type,
    extension_of,
    hamming_distance,
    image_phash,
    original_dir,
    safe_filename,
    validate_stored_path,
    verify_magic,
)
from app.utils.logging import get_logger
from app.utils.time import utcnow

logger = get_logger(__name__)


@dataclass
class DuplicateHit:
    evidence: Evidence
    similarity: float
    kind: str


@dataclass
class StoredUpload:
    evidence: Evidence
    duplicates: list[DuplicateHit] = field(default_factory=list)


def get_or_create_default_user(db: Session, actor: str | None = None) -> User:
    email = settings.default_actor_email
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(email=email, display_name=actor or settings.default_actor, role="analyst")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def evidence_reference() -> str:
    return f"TV-{utcnow().year}-{uuid.uuid4().hex[:6].upper()}"


async def store_upload(
    db: Session,
    upload: UploadFile,
    user: User,
    *,
    capture: dict[str, Any] | None = None,
    auto_detect: bool = False,
) -> StoredUpload:
    original_name = upload.filename or "evidence"
    clean_name = safe_filename(original_name)
    try:
        file_type, mime = detect_file_type(clean_name, upload.content_type)
    except ValueError as exc:
        raise UnsupportedMediaError(str(exc), {"filename": original_name}) from exc

    tmp_dir = settings.upload_root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}.part"

    digest = hashlib.sha256()
    size = 0
    try:
        with tmp_path.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise FileTooLargeError(settings.max_upload_mb)
                digest.update(chunk)
                handle.write(chunk)
        if size == 0:
            raise UnsupportedMediaError("Empty files cannot be preserved.", {"filename": original_name})
        if not verify_magic(tmp_path, extension_of(clean_name)):
            raise UnsupportedMediaError(
                "The file signature does not match its extension.",
                {"filename": original_name, "extension": extension_of(clean_name)},
            )

        sha256 = digest.hexdigest()
        exact = db.scalar(
            select(Evidence).where(Evidence.sha256 == sha256, Evidence.deleted_at.is_(None)).limit(1)
        )
        duplicates: list[DuplicateHit] = []
        if exact:
            duplicates.append(DuplicateHit(exact, 1.0, "exact"))

        phash = image_phash(tmp_path) if file_type.value == "image" else None
        if phash:
            candidates = db.scalars(
                select(Evidence).where(Evidence.phash.is_not(None), Evidence.deleted_at.is_(None))
            ).all()
            for candidate in candidates:
                if exact and candidate.id == exact.id:
                    continue
                distance = hamming_distance(phash, candidate.phash or "")
                if distance <= 5:
                    duplicates.append(DuplicateHit(candidate, round(1 - distance / 64, 3), "perceptual"))

        evidence_id = uuid.uuid4()
        destination_dir = original_dir(evidence_id)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / clean_name
        shutil.move(str(tmp_path), str(destination))
        if settings.read_only_originals:
            try:
                os.chmod(destination, stat.S_IREAD)
            except OSError:  # pragma: no cover - Windows locks/permissions
                logger.warning("Could not mark original read-only: %s", destination)

        capture_data = {key: value for key, value in (capture or {}).items() if value}
        meta = {
            "extension": extension_of(clean_name),
            "declared_content_type": upload.content_type,
            "sha256": sha256,
            "phash": phash,
            "source": "Upload",
            "tags": list(
                dict.fromkeys(
                    [
                        "new intake",
                        *([capture_data["location"]] if capture_data.get("location") else []),
                        *(capture_data.get("persons") or []),
                    ]
                )
            )[:6],
        }
        if capture_data:
            meta["capture"] = capture_data
        if auto_detect:
            meta["captureAutoDetect"] = True
        evidence = Evidence(
            id=evidence_id,
            reference=evidence_reference(),
            original_filename=original_name,
            stored_filename=clean_name,
            file_path=str(destination),
            mime_type=mime,
            file_type=file_type,
            size_bytes=size,
            sha256=sha256,
            phash=phash,
            source="Upload",
            status=EvidenceStatus.PENDING,
            processing_stage=ProcessingStage.QUEUED,
            processing_progress=0,
            integrity_status=IntegrityStatus.PENDING,
            duplicate_of_id=exact.id if exact else None,
            uploaded_by_id=user.id,
            note=capture_data.get("note") or "Queued for extraction.",
            meta=meta,
            uploaded_at=utcnow(),
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        record_audit(
            db,
            actor=user.display_name,
            action="Evidence uploaded",
            target_type="evidence",
            target_id=str(evidence.id),
            details={
                "filename": original_name,
                "sha256": sha256,
                "size": size,
                "duplicateOf": str(exact.id) if exact else None,
                "similarTo": [str(d.evidence.id) for d in duplicates if d.kind == "perceptual"],
            },
        )
        return StoredUpload(evidence=evidence, duplicates=duplicates)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def get_active_evidence(db: Session, evidence_id: uuid.UUID) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if not evidence or evidence.deleted_at is not None:
        raise NotFoundError("Evidence", evidence_id)
    return evidence


def resolve_original(evidence: Evidence) -> Path:
    path = validate_stored_path(evidence.file_path)
    if not path.exists():
        raise NotFoundError("Evidence file", evidence.id)
    return path


def soft_delete(db: Session, evidence: Evidence, actor: str, ip: str | None = None) -> None:
    evidence.deleted_at = utcnow()
    evidence.note = "Removed from the active vault. Original file is retained for custody."
    db.add(evidence)
    db.commit()
    record_audit(
        db,
        actor=actor,
        action="Evidence removed from vault",
        target_type="evidence",
        target_id=str(evidence.id),
        details={"filename": evidence.original_filename, "retainedOriginal": True},
        ip_address=ip,
    )
