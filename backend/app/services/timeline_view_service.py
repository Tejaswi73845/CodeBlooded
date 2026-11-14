from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Entity, EventEntity, Evidence, TimelineEvent
from app.models.enums import EntityType, EventCategory
from app.schemas.timeline import TimelineEventOut, TimelineEventUpdate, TimelinePage, TimelinePerson
from app.utils.text import truncate


def query_timeline(
    db: Session,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    person_id: uuid.UUID | None = None,
    category: str | None = None,
    evidence_id: uuid.UUID | None = None,
    uncertain: bool | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    workspace_id: uuid.UUID | None = None,
) -> TimelinePage:
    stmt = (
        select(TimelineEvent)
        .join(Evidence, Evidence.id == TimelineEvent.evidence_id)
        .where(Evidence.deleted_at.is_(None))
    )
    if workspace_id is not None:
        stmt = stmt.where(Evidence.workspace_id == workspace_id)
    if from_date:
        stmt = stmt.where(TimelineEvent.occurred_at.is_not(None), TimelineEvent.occurred_at >= from_date)
    if to_date:
        stmt = stmt.where(TimelineEvent.occurred_at.is_not(None), TimelineEvent.occurred_at <= to_date)
    if person_id:
        stmt = stmt.where(
            TimelineEvent.id.in_(select(EventEntity.event_id).where(EventEntity.entity_id == person_id))
        )
    if evidence_id:
        stmt = stmt.where(TimelineEvent.evidence_id == evidence_id)
    if uncertain is not None:
        stmt = stmt.where(TimelineEvent.time_uncertain.is_(uncertain))
    if category and category != "all":
        try:
            stmt = stmt.where(TimelineEvent.category == EventCategory(category))
        except ValueError:
            pass
    if q and q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(TimelineEvent.title.ilike(needle), TimelineEvent.description.ilike(needle)))

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at, TimelineEvent.created_at)
            .limit(limit)
            .offset(offset)
        ).all()
    )
    earliest = db.scalar(
        select(func.min(TimelineEvent.occurred_at))
        .join(Evidence)
        .where(
            Evidence.deleted_at.is_(None),
            Evidence.workspace_id == workspace_id if workspace_id is not None else True,
        )
    )
    latest = db.scalar(
        select(func.max(TimelineEvent.occurred_at))
        .join(Evidence)
        .where(
            Evidence.deleted_at.is_(None),
            Evidence.workspace_id == workspace_id if workspace_id is not None else True,
        )
    )
    uncertain_count = int(
        db.scalar(
            select(func.count(TimelineEvent.id))
            .join(Evidence)
            .where(
                Evidence.deleted_at.is_(None),
                TimelineEvent.time_uncertain.is_(True),
                Evidence.workspace_id == workspace_id if workspace_id is not None else True,
            )
        )
        or 0
    )
    return TimelinePage(
        items=_serialize_many(db, rows),
        total=total,
        limit=limit,
        offset=offset,
        earliest=earliest,
        latest=latest,
        uncertain_count=uncertain_count,
    )


def get_timeline_event(db: Session, event_id: uuid.UUID, workspace_id: uuid.UUID | None = None) -> TimelineEventOut:
    event = db.get(TimelineEvent, event_id)
    if not event:
        raise NotFoundError("Timeline event", event_id)
    if workspace_id is not None:
        evidence = db.get(Evidence, event.evidence_id)
        if not evidence or evidence.workspace_id != workspace_id:
            raise NotFoundError("Timeline event", event_id)
    return _serialize_many(db, [event])[0]


def update_timeline_event(
    db: Session,
    event_id: uuid.UUID,
    workspace_id: uuid.UUID | None,
    payload: TimelineEventUpdate,
) -> TimelineEventOut:
    event = db.get(TimelineEvent, event_id)
    if not event:
        raise NotFoundError("Timeline event", event_id)
    evidence = db.get(Evidence, event.evidence_id)
    if not evidence or (workspace_id is not None and evidence.workspace_id != workspace_id):
        raise NotFoundError("Timeline event", event_id)

    if payload.title is not None:
        title = payload.title.strip()
        if title:
            event.title = title[:300]
    if payload.description is not None:
        event.description = payload.description.strip()[:4000]

    if payload.location is not None:
        meta = dict(event.meta or {})
        location = payload.location.strip()
        if location:
            meta["location"] = location[:300]
        else:
            meta.pop("location", None)
        event.meta = meta

    if payload.date is not None:
        date = payload.date.strip()
        if not date:
            event.occurred_at = None
            event.occurred_at_raw = payload.occurred_at_raw or None
            event.time_uncertain = True
        else:
            time = (payload.time or "00:00").strip() or "00:00"
            try:
                event.occurred_at = datetime.fromisoformat(f"{date}T{time}")
                event.time_uncertain = not bool(payload.time and payload.time.strip())
                event.occurred_at_raw = (
                    payload.occurred_at_raw
                    or (f"{date} {time}" if payload.time and payload.time.strip() else date)
                )[:255]
            except ValueError:
                raise ValueError("Invalid date/time supplied.")

    # Any manual change invalidates the cached AI summary.
    meta = dict(event.meta or {})
    meta.pop("aiSummary", None)
    event.meta = meta
    db.add(event)
    db.commit()
    db.refresh(event)
    return _serialize_many(db, [event])[0]


def _serialize_many(db: Session, rows: list[TimelineEvent]) -> list[TimelineEventOut]:
    if not rows:
        return []
    evidence_ids = list({event.evidence_id for event in rows})
    evidence_rows = db.scalars(select(Evidence).where(Evidence.id.in_(evidence_ids))).all()
    evidence_map = {row.id: row for row in evidence_rows}

    event_ids = [event.id for event in rows]
    links = db.execute(
        select(EventEntity.event_id, Entity)
        .join(Entity, Entity.id == EventEntity.entity_id)
        .where(EventEntity.event_id.in_(event_ids), Entity.type == EntityType.PERSON)
    ).all()
    people_map: dict[uuid.UUID, list[Entity]] = {}
    for event_id, entity in links:
        people_map.setdefault(event_id, []).append(entity)

    output: list[TimelineEventOut] = []
    for event in rows:
        evidence = evidence_map.get(event.evidence_id)
        people = people_map.get(event.id, [])
        output.append(
            TimelineEventOut(
                id=event.id,
                at=event.occurred_at,
                at_raw=event.occurred_at_raw,
                time_uncertain=event.time_uncertain,
                title=event.title,
                description=truncate(event.description, 1600),
                summary=(event.meta or {}).get("aiSummary", {}).get("summary")
                if isinstance((event.meta or {}).get("aiSummary"), dict)
                else None,
                category=event.category.value,
                severity=event.severity,
                confidence=event.confidence,
                evidence_id=event.evidence_id,
                evidence_ids=[event.evidence_id],
                evidence_name=evidence.original_filename if evidence else "Unknown",
                evidence_type=evidence.file_type.value if evidence else "data",
                person_ids=[person.id for person in people],
                people=[
                    TimelinePerson(id=person.id, name=person.value, confidence=person.confidence)
                    for person in people
                ],
                page_number=event.page_number,
                timestamp_start=event.source_timestamp,
                timestamp_end=(event.meta or {}).get("timestampEnd"),
                source_excerpt=truncate(event.source_excerpt or "", 800),
                location=(event.meta or {}).get("location"),
                extraction_source=event.extraction_source,
            )
        )
    return output
