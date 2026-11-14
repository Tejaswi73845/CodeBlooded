from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entity, EntityRelationship, EventEntity, Evidence, EvidenceEntity, TimelineEvent
from app.models.enums import EntityType, EventCategory
from app.services.entity_service import normalize_entity
from app.utils.logging import get_logger
from app.utils.text import truncate
from app.utils.time import utcnow

logger = get_logger(__name__)

CAPTURE_SOURCE = "capture"
CAPTURE_CONTEXT = "Capture details"


def sync_capture(db: Session, evidence: Evidence, capture: dict | None = None) -> None:
    """Materialise analyst/detected capture details as entities, edges and a timeline event."""
    capture = capture if capture is not None else (evidence.meta or {}).get("capture") or {}
    _clear_capture_artifacts(db, evidence)

    persons = [str(name).strip() for name in (capture.get("persons") or []) if str(name).strip()]
    location = str(capture.get("location") or "").strip() or None
    occurred_raw = capture.get("occurredAt")
    occurred_at: datetime | None = None
    if occurred_raw:
        try:
            occurred_at = datetime.fromisoformat(str(occurred_raw).replace("Z", "+00:00"))
        except ValueError:
            occurred_at = None

    entities: list[Entity] = []
    for name in persons[:10]:
        entity = _get_or_create(db, EntityType.PERSON, name)
        _link(db, evidence, entity)
        entities.append(entity)
    if location:
        entity = _get_or_create(db, EntityType.LOCATION, location)
        _link(db, evidence, entity)
        entities.append(entity)

    for index, left in enumerate(entities):
        for right in entities[index + 1 :]:
            if _relationship_exists(db, evidence, left, right):
                continue
            db.add(
                EntityRelationship(
                    from_entity_id=left.id,
                    to_entity_id=right.id,
                    evidence_id=evidence.id,
                    relationship_type=_relationship_type(left.type, right.type),
                    context=CAPTURE_CONTEXT,
                    confidence=0.9,
                )
            )

    if occurred_at or location or persons or capture.get("note"):
        event = TimelineEvent(
            evidence_id=evidence.id,
            occurred_at=occurred_at,
            occurred_at_raw=str(occurred_raw) if occurred_raw else None,
            time_uncertain=occurred_at is None,
            title=truncate(f"Evidence captured — {evidence.original_filename}", 250),
            description=truncate(capture.get("note") or "Capture details recorded for this evidence.", 1200),
            category=EventCategory.OTHER,
            severity="info",
            confidence=0.9,
            extraction_source=CAPTURE_SOURCE,
            meta={"location": location} if location else {},
        )
        db.add(event)
        db.flush()
        for entity in entities:
            db.add(EventEntity(event_id=event.id, entity_id=entity.id, role=entity.type.value))

    db.commit()
    if entities or occurred_at:
        logger.info(
            "Capture metadata synced for %s: %s people, location=%s",
            evidence.id,
            len(persons),
            bool(location),
        )


def _clear_capture_artifacts(db: Session, evidence: Evidence) -> None:
    for link in db.scalars(select(EvidenceEntity).where(EvidenceEntity.evidence_id == evidence.id)).all():
        if (link.meta or {}).get("source") == CAPTURE_SOURCE:
            db.delete(link)
    for rel in db.scalars(select(EntityRelationship).where(EntityRelationship.evidence_id == evidence.id)).all():
        if rel.context == CAPTURE_CONTEXT:
            db.delete(rel)
    for event in db.scalars(
        select(TimelineEvent).where(
            TimelineEvent.evidence_id == evidence.id,
            TimelineEvent.extraction_source == CAPTURE_SOURCE,
        )
    ).all():
        db.delete(event)
    db.commit()


def _get_or_create(db: Session, entity_type: EntityType, value: str) -> Entity:
    normalized = normalize_entity(entity_type, value)
    entity = db.scalar(
        select(Entity).where(Entity.type == entity_type, Entity.normalized_value == normalized)
    )
    if entity:
        entity.mention_count += 1
        entity.last_seen_at = utcnow()
        db.add(entity)
        return entity
    entity = Entity(
        type=entity_type,
        value=value[:500],
        normalized_value=normalized[:500],
        confidence=0.9,
        source="analyst",
        mention_count=1,
        meta={"fromCapture": True},
    )
    db.add(entity)
    db.flush()
    return entity


def _link(db: Session, evidence: Evidence, entity: Entity) -> None:
    link = db.get(EvidenceEntity, {"evidence_id": evidence.id, "entity_id": entity.id})
    if link:
        return
    db.add(
        EvidenceEntity(
            evidence_id=evidence.id,
            entity_id=entity.id,
            occurrence_count=1,
            excerpt="Capture details",
            meta={"source": CAPTURE_SOURCE},
        )
    )


def _relationship_exists(db: Session, evidence: Evidence, left: Entity, right: Entity) -> bool:
    pair = select(EntityRelationship).where(
        EntityRelationship.evidence_id == evidence.id,
        EntityRelationship.context == CAPTURE_CONTEXT,
    )
    for rel in db.scalars(pair).all():
        ids = {rel.from_entity_id, rel.to_entity_id}
        if ids == {left.id, right.id}:
            return True
    return False


def _relationship_type(left: EntityType, right: EntityType) -> str:
    types = {left, right}
    if EntityType.PERSON in types and EntityType.LOCATION in types:
        return "person_location"
    if EntityType.PERSON in types:
        return "person_person"
    return "mentioned_together"
