from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import (
    DocumentChunk,
    Entity,
    EntityRelationship,
    EventEntity,
    Evidence,
    EvidenceEntity,
    ExtractedContent,
    TimelineEvent,
)
from app.models.enums import AuditResult, ContentKind, EntityType, EvidenceStatus, ProcessingStage
from app.services.audit_service import record_audit
from app.services.audio_service import probe_media, transcribe_audio
from app.services.capture_service import sync_capture
from app.services.entity_service import ExtractionResult, extract_entities_for_evidence
from app.services.integrity_service import verify_evidence_integrity
from app.services.ocr_service import extract_image_text
from app.services.pdf_service import extract_pdf
from app.services.rag_service import index_evidence
from app.services.timeline_service import build_timeline_for_evidence, clear_timeline
from app.services.video_service import extract_video_assets
from app.utils.files import derived_dir, validate_stored_path
from app.utils.logging import get_logger
from app.utils.text import clean_text, truncate
from app.utils.time import format_duration, utcnow

logger = get_logger(__name__)

# Heavy OCR/ASR models are CPU-bound; serialise local processing to protect memory
# and avoid competing FFmpeg/Whisper jobs. Swap for a queue (RQ/Celery) when scaling.
_pipeline_lock = threading.Lock()


def set_stage(db: Session, evidence: Evidence, stage: ProcessingStage, progress: int) -> None:
    evidence.processing_stage = stage
    evidence.processing_progress = max(0, min(100, progress))
    db.add(evidence)
    db.commit()


def process_evidence(evidence_id: str) -> None:
    with _pipeline_lock:
        _process_evidence(evidence_id)


def _process_evidence(evidence_id: str) -> None:
    """Runs one evidence item. Opens its own session; never relies on request state."""
    db = SessionLocal()
    evidence: Evidence | None = None
    try:
        evidence = db.get(Evidence, uuid.UUID(str(evidence_id)))
        if not evidence or evidence.deleted_at is not None:
            return
        if evidence.status == EvidenceStatus.PROCESSING:
            logger.info("Evidence %s is already processing", evidence_id)
            return

        evidence.status = EvidenceStatus.PROCESSING
        evidence.processing_stage = ProcessingStage.STARTING
        evidence.processing_progress = 3
        evidence.processing_started_at = utcnow()
        evidence.processing_completed_at = None
        evidence.error_message = None
        evidence.meta = {
            key: value
            for key, value in (evidence.meta or {}).items()
            if key not in {"audioError", "extractionLimitations", "note"}
        }
        db.add(evidence)
        db.commit()
        record_audit(
            db,
            actor="System",
            action="Processing started",
            target_type="evidence",
            target_id=str(evidence.id),
            details={"filename": evidence.original_filename, "type": evidence.file_type.value},
        )

        reset_derived(db, evidence.id)
        set_stage(db, evidence, ProcessingStage.TEXT_EXTRACTION, 10)
        contents, metadata = _extract(db, evidence)
        _merge_metadata(evidence, metadata)
        db.add(evidence)
        db.commit()

        set_stage(db, evidence, ProcessingStage.RAG_INDEXING, 66)
        rag_stats = index_evidence(db, evidence)
        evidence.meta = {
            **(evidence.meta or {}),
            "ragChunks": rag_stats.chunks,
            "ragEmbedded": rag_stats.embedded,
            "ragEmbeddingModel": rag_stats.model,
        }
        if rag_stats.errors:
            evidence.meta["ragLimitations"] = rag_stats.errors[:3]
        db.add(evidence)
        db.commit()

        set_stage(db, evidence, ProcessingStage.ENTITY_EXTRACTION, 74)

        extraction = extract_entities_for_evidence(db, evidence, contents)
        _refresh_mentions(db, [link.entity_id for link in evidence.entity_links])
        set_stage(db, evidence, ProcessingStage.TIMELINE_RECONSTRUCTION, 88)

        clear_timeline(db, evidence.id)
        timeline = build_timeline_for_evidence(db, evidence, contents, extraction.events)

        if (evidence.meta or {}).get("captureAutoDetect") and _detect_capture(evidence, extraction):
            db.add(evidence)
            db.commit()

        capture = (evidence.meta or {}).get("capture")
        if capture:
            sync_capture(db, evidence, capture)

        set_stage(db, evidence, ProcessingStage.INTEGRITY_CHECK, 94)
        integrity = verify_evidence_integrity(db, evidence, actor="System")

        evidence.status = EvidenceStatus.COMPLETED
        evidence.processing_stage = ProcessingStage.COMPLETED
        evidence.processing_progress = 100
        evidence.processing_completed_at = utcnow()
        evidence.note = _note_for(evidence, contents, extraction, timeline.created)
        if extraction.limitations:
            evidence.meta = {
                **(evidence.meta or {}),
                "extractionLimitations": extraction.limitations,
            }
        db.add(evidence)
        db.commit()
        record_audit(
            db,
            actor="System",
            action="Processing completed",
            target_type="evidence",
            target_id=str(evidence.id),
            details={
                "contents": len(contents),
                "entities": extraction.stored_entities,
                "relationships": extraction.relationships,
                "events": timeline.created,
                "provider": extraction.provider,
                "integrity": integrity.value,
                "ragChunks": rag_stats.chunks,
                "ragEmbedded": rag_stats.embedded,
                "ragErrors": rag_stats.errors[:3],
            },
        )
    except Exception as exc:  # noqa: BLE001 - background failures belong in evidence state
        logger.exception("Processing failed for evidence %s", evidence_id)
        db.rollback()
        try:
            if evidence is None:
                evidence = db.get(Evidence, uuid.UUID(str(evidence_id)))
            if evidence:
                evidence.status = EvidenceStatus.FAILED
                evidence.processing_stage = ProcessingStage.FAILED
                evidence.error_message = _friendly_error(exc)
                evidence.processing_completed_at = utcnow()
                db.add(evidence)
                db.commit()
                record_audit(
                    db,
                    actor="System",
                    action="Processing failed",
                    target_type="evidence",
                    target_id=str(evidence.id),
                    result=AuditResult.WARNING,
                    details={"error": evidence.error_message, "filename": evidence.original_filename},
                )
        except Exception:  # pragma: no cover - last-resort guard
            logger.exception("Could not persist failure state for evidence %s", evidence_id)
    finally:
        db.close()


def _detect_capture(evidence: Evidence, extraction: ExtractionResult) -> bool:
    """Fill missing capture details from what extraction found in the file itself."""
    meta = evidence.meta or {}
    capture = dict(meta.get("capture") or {})
    detected: list[str] = list(capture.get("detected") or [])
    changed = False

    if not capture.get("occurredAt"):
        occurred = _detect_occurred_at(evidence, extraction)
        if occurred:
            capture["occurredAt"] = occurred
            detected.append("occurredAt")
            changed = True

    if not capture.get("location"):
        location = next(
            (
                entity.value.strip()
                for entity in extraction.entities
                if entity.type == EntityType.LOCATION and entity.value.strip()
            ),
            None,
        )
        if location:
            capture["location"] = location
            detected.append("location")
            changed = True

    if not capture.get("persons"):
        persons: list[str] = []
        for entity in extraction.entities:
            if entity.type != EntityType.PERSON:
                continue
            name = entity.value.strip()
            if name and name not in persons:
                persons.append(name)
        if persons:
            capture["persons"] = persons[:5]
            detected.append("persons")
            changed = True

    if changed:
        evidence.meta = {
            **meta,
            "capture": {**capture, "detected": sorted(set(detected))},
        }
        logger.info("Auto-detected capture details for %s: %s", evidence.id, sorted(set(detected)))
    return changed


def _detect_occurred_at(evidence: Evidence, extraction: ExtractionResult) -> str | None:
    exif = (evidence.meta or {}).get("exif") or {}
    raw_exif = exif.get("36867") or exif.get("306")
    if raw_exif:
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(str(raw_exif), fmt).isoformat()
            except ValueError:
                continue
    dated = [event.occurred_at for event in extraction.events if event.occurred_at]
    if dated:
        return min(dated).isoformat()
    return None


def reset_derived(db: Session, evidence_id: uuid.UUID) -> None:
    event_ids = select(TimelineEvent.id).where(TimelineEvent.evidence_id == evidence_id)
    db.execute(delete(EventEntity).where(EventEntity.event_id.in_(event_ids)))
    db.execute(delete(TimelineEvent).where(TimelineEvent.evidence_id == evidence_id))
    db.execute(delete(EntityRelationship).where(EntityRelationship.evidence_id == evidence_id))
    db.execute(delete(EvidenceEntity).where(EvidenceEntity.evidence_id == evidence_id))
    db.execute(delete(DocumentChunk).where(DocumentChunk.evidence_id == evidence_id))
    db.execute(delete(ExtractedContent).where(ExtractedContent.evidence_id == evidence_id))
    db.commit()


def _extract(db: Session, evidence: Evidence) -> tuple[list[ExtractedContent], dict[str, Any]]:
    path = validate_stored_path(evidence.file_path)

    if evidence.file_type.value == "image":
        return _extract_image(db, evidence, path)
    if evidence.file_type.value == "document":
        return _extract_pdf(db, evidence, path)
    if evidence.file_type.value == "audio":
        return _extract_audio(db, evidence, path)
    if evidence.file_type.value == "video":
        return _extract_video(db, evidence, path)
    return _extract_text(db, evidence, path)


def _extract_image(db: Session, evidence: Evidence, path: Path) -> tuple[list[ExtractedContent], dict[str, Any]]:
    metadata: dict[str, Any] = {}
    try:
        from PIL import Image

        with Image.open(path) as image:
            metadata.update(
                {
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                    "mode": image.mode,
                    "preview": f"{image.width} × {image.height} · {image.format or 'Image'} · OCR",
                }
            )
            try:
                exif = image.getexif()
                selected = {
                    str(tag): str(value)
                    for tag, value in exif.items()
                    if tag in {271, 272, 274, 305, 306, 36867, 36868}
                }
                if selected:
                    metadata["exif"] = selected
            except Exception:  # noqa: BLE001 - corrupt EXIF should not fail OCR
                pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image metadata failed for %s: %s", evidence.id, exc)
        metadata["preview"] = "Image · OCR"

    set_stage(db, evidence, ProcessingStage.TEXT_EXTRACTION, 25)
    ocr = extract_image_text(path)
    content = ExtractedContent(
        evidence_id=evidence.id,
        kind=ContentKind.OCR,
        text=ocr.text,
        confidence=ocr.confidence,
        language=ocr.language or settings.ocr_languages.split(",")[0],
        meta={
            "provider": ocr.provider,
            "blocks": [
                {
                    "text": block.text,
                    "confidence": float(block.confidence),
                    "x": float(block.x),
                    "y": float(block.y),
                    "width": float(block.width),
                    "height": float(block.height),
                }
                for block in ocr.blocks[:200]
            ],
            "width": metadata.get("width"),
            "height": metadata.get("height"),
        },
    )
    db.add(content)
    db.commit()
    metadata.update({"ocrEngine": ocr.provider, "ocrConfidence": ocr.confidence, "textCharacters": len(ocr.text)})
    if not ocr.text:
        metadata["note"] = "No readable text was detected in the image."
    return [content], metadata


def _extract_pdf(db: Session, evidence: Evidence, path: Path) -> tuple[list[ExtractedContent], dict[str, Any]]:
    set_stage(db, evidence, ProcessingStage.TEXT_EXTRACTION, 22)
    result = extract_pdf(path, evidence.id)
    contents: list[ExtractedContent] = []
    for page in result.pages:
        content = ExtractedContent(
            evidence_id=evidence.id,
            kind=ContentKind.PDF_OCR if page.kind == "pdf_ocr" else ContentKind.PDF_TEXT,
            text=page.text,
            confidence=page.confidence,
            page_number=page.page_number,
            meta={"provider": page.provider, **page.meta},
        )
        db.add(content)
        contents.append(content)
    db.commit()
    metadata = {
        **result.metadata,
        "preview": f"PDF · {result.page_count} pages · {len([p for p in result.pages if p.text])} readable",
        "textCharacters": sum(len(page.text) for page in result.pages),
    }
    return contents, metadata


def _extract_audio(db: Session, evidence: Evidence, path: Path) -> tuple[list[ExtractedContent], dict[str, Any]]:
    work_dir = derived_dir(evidence.id)
    work_dir.mkdir(parents=True, exist_ok=True)
    set_stage(db, evidence, ProcessingStage.AUDIO_TRANSCRIPTION, 25)
    probe = probe_media(path)
    duration = probe.get("duration")
    transcript = transcribe_audio(path, work_dir)
    content = ExtractedContent(
        evidence_id=evidence.id,
        kind=ContentKind.TRANSCRIPT,
        text=transcript.text,
        confidence=transcript.confidence,
        language=transcript.language,
        timestamp_start=0.0,
        timestamp_end=transcript.duration or duration,
        meta={
            "segments": [
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": segment.text,
                    "confidence": float(segment.confidence) if segment.confidence is not None else None,
                }
                for segment in transcript.segments
            ],
            "model": transcript.model,
            "provider": "whisper",
        },
    )
    db.add(content)
    db.commit()
    metadata = {
        **probe,
        "duration": transcript.duration or duration,
        "preview": f"Audio · {format_duration(transcript.duration or duration) or 'transcribed'} · "
        f"{transcript.language or 'auto'} · Whisper",
        "transcriptSegments": len(transcript.segments),
        "textCharacters": len(transcript.text),
    }
    if not transcript.text:
        metadata["note"] = "No speech was detected in this recording."
    return [content], metadata


def _extract_video(db: Session, evidence: Evidence, path: Path) -> tuple[list[ExtractedContent], dict[str, Any]]:
    work_dir = derived_dir(evidence.id)
    work_dir.mkdir(parents=True, exist_ok=True)
    set_stage(db, evidence, ProcessingStage.TEXT_EXTRACTION, 18)
    video = extract_video_assets(path, work_dir)
    contents: list[ExtractedContent] = []
    transcribed = False
    if video.audio_path:
        try:
            set_stage(db, evidence, ProcessingStage.AUDIO_TRANSCRIPTION, 32)
            transcript = transcribe_audio(video.audio_path, work_dir)
            if transcript.text:
                content = ExtractedContent(
                    evidence_id=evidence.id,
                    kind=ContentKind.TRANSCRIPT,
                    text=transcript.text,
                    confidence=transcript.confidence,
                    language=transcript.language,
                    timestamp_start=0.0,
                    timestamp_end=transcript.duration or video.metadata.get("duration"),
                    meta={
                        "segments": [
                            {
                                "start": float(s.start),
                                "end": float(s.end),
                                "text": s.text,
                                "confidence": float(s.confidence) if s.confidence is not None else None,
                            }
                            for s in transcript.segments
                        ],
                        "model": transcript.model,
                        "provider": "whisper",
                    },
                )
                db.add(content)
                contents.append(content)
                transcribed = True
                db.commit()
        except Exception as exc:  # noqa: BLE001 - continue with frames
            logger.warning("Video audio transcription failed for %s: %s %s", evidence.id, exc, getattr(exc, "details", ""))
            video.metadata["audioError"] = truncate(str(exc), 300)

    frame_results: list[dict[str, Any]] = []
    frame_content_count = 0
    for frame in video.frames:
        set_stage(
            db,
            evidence,
            ProcessingStage.TEXT_EXTRACTION,
            min(60, 40 + int(20 * (frame.index + 1) / max(1, len(video.frames)))),
        )
        try:
            ocr = extract_image_text(frame.path)
        except Exception as exc:  # noqa: BLE001 - one unreadable frame must not fail the video
            logger.warning("Frame OCR failed for %s at %.1fs: %s", evidence.id, frame.timestamp, exc)
            frame_results.append({"timestamp": frame.timestamp, "text": "", "error": truncate(str(exc), 160)})
            continue
        if ocr.text:
            duration = video.metadata.get("duration")
            frame_end = frame.timestamp + settings.video_frame_interval_seconds
            if duration:
                frame_end = min(frame_end, float(duration))
            content = ExtractedContent(
                evidence_id=evidence.id,
                kind=ContentKind.FRAME_OCR,
                text=ocr.text,
                confidence=ocr.confidence,
                timestamp_start=frame.timestamp,
                timestamp_end=frame_end,
                frame_path=str(frame.path),
                meta={"provider": ocr.provider, "frameIndex": frame.index},
            )
            db.add(content)
            contents.append(content)
            frame_content_count += 1
        frame_results.append(
            {"timestamp": frame.timestamp, "text": truncate(ocr.text, 300), "confidence": ocr.confidence}
        )
    db.commit()
    metadata = {
        **video.metadata,
        "framesOcr": frame_content_count,
        "frameResults": frame_results[:24],
        "transcribed": transcribed,
        "textCharacters": sum(len(content.text) for content in contents),
    }
    metadata.setdefault(
        "preview",
        f"Video · {format_duration(video.metadata.get('duration')) or '—'} · {len(video.frames)} frames",
    )
    if not contents:
        metadata["note"] = "No readable text or speech was detected in this video."
    return contents, metadata


def _extract_text(db: Session, evidence: Evidence, path: Path) -> tuple[list[ExtractedContent], dict[str, Any]]:
    set_stage(db, evidence, ProcessingStage.TEXT_EXTRACTION, 30)
    limit = 5 * 1024 * 1024
    raw = path.read_bytes()
    truncated = len(raw) > limit
    if truncated:
        raw = raw[:limit]
    text = ""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    text = clean_text(text)
    if evidence.file_type.value == "data" and evidence.mime_type == "application/json":
        try:
            parsed = json.loads(text)
            meta = {"jsonValid": True, "jsonType": type(parsed).__name__}
        except json.JSONDecodeError:
            meta = {"jsonValid": False}
    else:
        meta = {}
    content = ExtractedContent(
        evidence_id=evidence.id,
        kind=ContentKind.TEXT,
        text=text,
        confidence=0.99,
        meta={"provider": "local", "truncated": truncated, **meta},
    )
    db.add(content)
    db.commit()
    metadata = {
        "textCharacters": len(text),
        "preview": f"{evidence.file_type.value.title()} · {len(text):,} characters",
        "truncated": truncated,
    }
    if truncated:
        metadata["note"] = "Text was truncated at 5 MB for analysis; the original is preserved."
    return [content], metadata


def _merge_metadata(evidence: Evidence, metadata: dict[str, Any]) -> None:
    evidence.meta = {**(evidence.meta or {}), **metadata}
    if metadata.get("pages"):
        evidence.note = f"{metadata['pages']} pages preserved · text extracted."
    elif metadata.get("duration"):
        evidence.note = f"{format_duration(metadata['duration'])} of media preserved · transcribed."
    elif metadata.get("textCharacters"):
        evidence.note = f"{metadata['textCharacters']:,} characters extracted."


def _refresh_mentions(db: Session, entity_ids: list[uuid.UUID]) -> None:
    if not entity_ids:
        return
    for entity_id in set(entity_ids):
        entity = db.get(Entity, entity_id)
        if not entity:
            continue
        total = db.scalar(
            select(func.coalesce(func.sum(EvidenceEntity.occurrence_count), 0)).where(
                EvidenceEntity.entity_id == entity_id
            )
        )
        entity.mention_count = int(total or 0)
        db.add(entity)
    db.commit()


def _note_for(evidence: Evidence, contents: list[ExtractedContent], extraction: ExtractionResult, events: int) -> str:
    text_chars = sum(len(content.text) for content in contents)
    parts = [f"{text_chars:,} characters extracted"]
    if extraction.stored_entities:
        parts.append(f"{extraction.stored_entities} entities resolved")
    if events:
        parts.append(f"{events} timeline events reconstructed")
    if extraction.provider:
        parts.append(f"extraction: {extraction.provider}")
    return " · ".join(parts)


def _friendly_error(exc: Exception) -> str:
    from sqlalchemy.exc import SQLAlchemyError

    if isinstance(exc, SQLAlchemyError):
        return "Extracted data could not be persisted. The request ID is in the server logs."
    message = str(exc).split("[SQL:")[0].replace("\n", " ").strip()
    return truncate(f"{type(exc).__name__}: {message}", 400)


def reindex_evidence(evidence_id: uuid.UUID) -> None:
    process_evidence(str(evidence_id))
