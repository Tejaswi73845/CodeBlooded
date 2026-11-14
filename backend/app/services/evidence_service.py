from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Entity, Evidence, EvidenceEntity, TimelineEvent, User
from app.models.enums import EntityType, EvidenceStatus, FileType
from app.schemas.evidence import (
    DuplicateWarning,
    EntityBrief,
    EvidenceDetail,
    EvidenceSummary,
    ExtractedContentOut,
    TimelineBrief,
)
from app.utils.files import hamming_distance
from app.utils.text import truncate

STATUS_ALIASES = {"processed": EvidenceStatus.COMPLETED, "queued": EvidenceStatus.PENDING}


def _status(value: str | None) -> EvidenceStatus | None:
    if not value or value == "all":
        return None
    if value in STATUS_ALIASES:
        return STATUS_ALIASES[value]
    try:
        return EvidenceStatus(value)
    except ValueError:
        return None


def _file_type(value: str | None) -> FileType | None:
    if not value or value == "all":
        return None
    try:
        return FileType(value)
    except ValueError:
        return None


def list_evidence(
    db: Session,
    *,
    q: str | None = None,
    file_type: str | None = None,
    status: str | None = None,
    entity_id: uuid.UUID | None = None,
    duplicate_only: bool = False,
    sort: str = "newest",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[EvidenceSummary], int]:
    stmt = select(Evidence).where(Evidence.deleted_at.is_(None))
    type_value = _file_type(file_type)
    if type_value:
        stmt = stmt.where(Evidence.file_type == type_value)
    status_value = _status(status)
    if status_value:
        stmt = stmt.where(Evidence.status == status_value)
    if duplicate_only:
        stmt = stmt.where(Evidence.duplicate_of_id.is_not(None))
    if entity_id:
        stmt = stmt.where(
            Evidence.id.in_(select(EvidenceEntity.evidence_id).where(EvidenceEntity.entity_id == entity_id))
        )
    if q and q.strip():
        needle = f"%{q.strip()}%"
        entity_matches = (
            select(EvidenceEntity.evidence_id)
            .join(Entity, Entity.id == EvidenceEntity.entity_id)
            .where(or_(Entity.value.ilike(needle), Entity.normalized_value.ilike(needle)))
        )
        stmt = stmt.where(
            or_(
                Evidence.original_filename.ilike(needle),
                Evidence.reference.ilike(needle),
                Evidence.sha256.ilike(needle),
                Evidence.note.ilike(needle),
                Evidence.id.in_(entity_matches),
            )
        )

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    order = {
        "oldest": Evidence.uploaded_at.asc(),
        "name": Evidence.original_filename.asc(),
        "size": Evidence.size_bytes.desc(),
        "newest": Evidence.uploaded_at.desc(),
    }.get(sort, Evidence.uploaded_at.desc())
    rows = list(db.scalars(stmt.order_by(order).limit(limit).offset(offset)).all())
    return serialize_evidence_many(db, rows), total


def serialize_evidence_many(db: Session, rows: list[Evidence]) -> list[EvidenceSummary]:
    if not rows:
        return []
    ids = [row.id for row in rows]
    user_names = {
        user_id: display
        for user_id, display in db.execute(select(User.id, User.display_name)).all()
    }
    person_rows = db.execute(
        select(EvidenceEntity.evidence_id, Entity.id)
        .join(Entity, Entity.id == EvidenceEntity.entity_id)
        .where(EvidenceEntity.evidence_id.in_(ids), Entity.type == EntityType.PERSON)
    ).all()
    persons: dict[uuid.UUID, list[uuid.UUID]] = {}
    for evidence_id, entity_id in person_rows:
        persons.setdefault(evidence_id, []).append(entity_id)

    event_rows = db.execute(
        select(TimelineEvent.evidence_id, TimelineEvent.id).where(TimelineEvent.evidence_id.in_(ids))
    ).all()
    events: dict[uuid.UUID, list[uuid.UUID]] = {}
    for evidence_id, event_id in event_rows:
        events.setdefault(evidence_id, []).append(event_id)

    tag_rows = db.execute(
        select(EvidenceEntity.evidence_id, Entity.value)
        .join(Entity, Entity.id == EvidenceEntity.entity_id)
        .where(
            EvidenceEntity.evidence_id.in_(ids),
            Entity.type.in_([EntityType.ORGANIZATION, EntityType.LOCATION]),
        )
    ).all()
    tags: dict[uuid.UUID, list[str]] = {}
    for evidence_id, value in tag_rows:
        tags.setdefault(evidence_id, []).append(value)

    output: list[EvidenceSummary] = []
    for evidence in rows:
        meta = evidence.meta or {}
        capture = meta.get("capture") or {}
        occurred_at = None
        raw_occurred = capture.get("occurredAt")
        if raw_occurred:
            try:
                occurred_at = datetime.fromisoformat(str(raw_occurred).replace("Z", "+00:00"))
            except ValueError:
                occurred_at = None
        output.append(
            EvidenceSummary(
                id=evidence.id,
                reference=evidence.reference,
                name=evidence.original_filename,
                type=evidence.file_type.value,
                mime=evidence.mime_type,
                size=evidence.size_bytes,
                uploaded_at=evidence.uploaded_at,
                uploaded_by=user_names.get(evidence.uploaded_by_id or uuid.UUID(int=0), "Analyst"),
                status=evidence.status.value,
                stage=evidence.processing_stage.value,
                progress=evidence.processing_progress,
                source=evidence.source,
                hash=evidence.sha256,
                integrity=evidence.integrity_status.value,
                person_ids=persons.get(evidence.id, []),
                event_ids=events.get(evidence.id, []),
                tags=list(dict.fromkeys([*(meta.get("tags") or []), *tags.get(evidence.id, [])[:3]]))[:6],
                duration=meta.get("duration"),
                pages=meta.get("pages"),
                note=evidence.note or meta.get("note"),
                preview=meta.get("preview"),
                duplicate_of=evidence.duplicate_of_id,
                error=evidence.error_message,
                verified_at=evidence.last_verified_at,
                occurred_at=occurred_at,
                location=capture.get("location"),
                persons=list(capture.get("persons") or []),
                capture_note=capture.get("note"),
                capture_detected=list(capture.get("detected") or []),
            )
        )
    return output


def serialize_evidence(db: Session, evidence: Evidence) -> EvidenceSummary:
    return serialize_evidence_many(db, [evidence])[0]


def get_detail(db: Session, evidence: Evidence) -> EvidenceDetail:
    base = serialize_evidence(db, evidence)
    contents = []
    for content in sorted(evidence.extracted_content, key=lambda item: (item.page_number or 0, item.created_at)):
        meta = dict(content.meta or {})
        text = content.text
        if len(text) > 8000:
            meta["textTruncated"] = True
            text = truncate(text, 8000)
        contents.append(
            ExtractedContentOut(
                id=content.id,
                kind=content.kind.value,
                text=text,
                language=content.language,
                confidence=content.confidence,
                page_number=content.page_number,
                timestamp_start=content.timestamp_start,
                timestamp_end=content.timestamp_end,
                meta=meta,
            )
        )

    entity_rows = db.execute(
        select(Entity)
        .join(EvidenceEntity, EvidenceEntity.entity_id == Entity.id)
        .where(EvidenceEntity.evidence_id == evidence.id)
        .order_by(Entity.type, Entity.mention_count.desc())
    ).scalars().all()
    entities = [
        EntityBrief(
            id=entity.id,
            type=entity.type.value,
            value=entity.value,
            normalized_value=entity.normalized_value,
            confidence=entity.confidence,
            mention_count=entity.mention_count,
        )
        for entity in entity_rows
    ]

    events = db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.evidence_id == evidence.id)
        .order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at, TimelineEvent.created_at)
    ).all()
    timeline = [
        TimelineBrief(
            id=event.id,
            at=event.occurred_at,
            at_raw=event.occurred_at_raw,
            time_uncertain=event.time_uncertain,
            title=event.title,
            category=event.category.value,
            confidence=event.confidence,
            evidence_id=event.evidence_id,
            page_number=event.page_number,
            source_timestamp=event.source_timestamp,
        )
        for event in events
    ]

    duplicates: list[DuplicateWarning] = []
    if evidence.duplicate_of_id:
        original = db.get(Evidence, evidence.duplicate_of_id)
        if original:
            duplicates.append(
                DuplicateWarning(
                    evidence_id=original.id,
                    reference=original.reference,
                    name=original.original_filename,
                    sha256=original.sha256,
                    similarity=1.0,
                    kind="exact",
                )
            )
    if evidence.phash:
        candidates = db.scalars(
            select(Evidence).where(
                Evidence.phash.is_not(None),
                Evidence.id != evidence.id,
                Evidence.deleted_at.is_(None),
            )
        ).all()
        for candidate in candidates:
            distance = hamming_distance(evidence.phash, candidate.phash or "")
            if distance <= 5:
                duplicates.append(
                    DuplicateWarning(
                        evidence_id=candidate.id,
                        reference=candidate.reference,
                        name=candidate.original_filename,
                        sha256=candidate.sha256,
                        similarity=round(1 - distance / 64, 3),
                        kind="perceptual",
                    )
                )

    return EvidenceDetail(
        **base.model_dump(),
        metadata=evidence.meta or {},
        extracted_content=contents,
        entities=entities,
        timeline_events=timeline,
        duplicates=duplicates,
    )
