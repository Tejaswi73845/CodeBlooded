from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Entity, EntityRelationship, EventEntity, Evidence, EvidenceEntity, TimelineEvent
from app.models.enums import EntityType
from app.schemas.entity import (
    EntityDetail,
    EntityEvidenceRef,
    EntityGraph,
    EntitySummary,
    GraphEdge,
    GraphNode,
    GraphStats,
    RelatedEntity,
)
from app.schemas.evidence import TimelineBrief

AUTO_GRAPH_TYPES = [
    EntityType.PERSON,
    EntityType.PHONE,
    EntityType.EMAIL,
    EntityType.ORGANIZATION,
    EntityType.LOCATION,
]


def _parse_types(types: str | None) -> list[EntityType]:
    if not types:
        return AUTO_GRAPH_TYPES
    values: list[EntityType] = []
    for raw in types.split(","):
        try:
            values.append(EntityType(raw.strip().lower()))
        except ValueError:
            continue
    return values or AUTO_GRAPH_TYPES


def _active_entity_ids():
    return (
        select(EvidenceEntity.entity_id)
        .join(Evidence, Evidence.id == EvidenceEntity.evidence_id)
        .where(Evidence.deleted_at.is_(None))
    )


def list_entities(
    db: Session,
    *,
    type_filter: str | None = None,
    q: str | None = None,
    evidence_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[EntitySummary], int]:
    stmt = select(Entity).where(Entity.id.in_(_active_entity_ids()))
    if type_filter:
        stmt = stmt.where(Entity.type.in_(_parse_types(type_filter)))
    if q and q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(Entity.value.ilike(needle), Entity.normalized_value.ilike(needle)))
    if evidence_id:
        stmt = stmt.where(
            Entity.id.in_(select(EvidenceEntity.entity_id).where(EvidenceEntity.evidence_id == evidence_id))
        )
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(stmt.order_by(Entity.mention_count.desc(), Entity.value).limit(limit).offset(offset)).all()
    )
    return _serialize_many(db, rows), total


def _serialize_many(db: Session, rows: list[Entity]) -> list[EntitySummary]:
    if not rows:
        return []
    ids = [row.id for row in rows]
    links = db.execute(
        select(EvidenceEntity.entity_id, EvidenceEntity.evidence_id, EvidenceEntity.occurrence_count)
        .join(Evidence, Evidence.id == EvidenceEntity.evidence_id)
        .where(EvidenceEntity.entity_id.in_(ids), Evidence.deleted_at.is_(None))
    ).all()
    by_entity: dict[uuid.UUID, list[uuid.UUID]] = {}
    mentions: dict[uuid.UUID, int] = {}
    for entity_id, evidence_id, occurrences in links:
        by_entity.setdefault(entity_id, []).append(evidence_id)
        mentions[entity_id] = mentions.get(entity_id, 0) + int(occurrences or 0)
    return [
        EntitySummary(
            id=row.id,
            type=row.type.value,
            value=row.value,
            normalized_value=row.normalized_value,
            confidence=row.confidence,
            source=row.source,
            mention_count=mentions.get(row.id, 0),
            evidence_count=len(set(by_entity.get(row.id, []))),
            evidence_ids=list(dict.fromkeys(by_entity.get(row.id, []))),
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            meta=row.meta or {},
        )
        for row in rows
    ]


def get_entity_detail(db: Session, entity_id: uuid.UUID) -> EntityDetail:
    entity = db.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", entity_id)
    active_links = db.scalar(
        select(func.count())
        .select_from(EvidenceEntity)
        .join(Evidence, Evidence.id == EvidenceEntity.evidence_id)
        .where(EvidenceEntity.entity_id == entity_id, Evidence.deleted_at.is_(None))
    )
    if not active_links:
        raise NotFoundError("Entity", entity_id)
    base = _serialize_many(db, [entity])[0]

    links = db.execute(
        select(EvidenceEntity, Evidence)
        .join(Evidence, Evidence.id == EvidenceEntity.evidence_id)
        .where(EvidenceEntity.entity_id == entity_id, Evidence.deleted_at.is_(None))
        .order_by(Evidence.uploaded_at.desc())
    ).all()
    evidence_refs: list[EntityEvidenceRef] = []
    evidence_ids: list[uuid.UUID] = []
    for link, evidence in links:
        evidence_ids.append(evidence.id)
        meta = link.meta or {}
        evidence_refs.append(
            EntityEvidenceRef(
                evidence_id=evidence.id,
                evidence_name=evidence.original_filename,
                excerpt=link.excerpt,
                occurrence_count=link.occurrence_count,
                page_number=meta.get("pageNumber"),
                timestamp_start=meta.get("timestampStart"),
            )
        )

    relationships = db.scalars(
        select(EntityRelationship)
        .join(Evidence, Evidence.id == EntityRelationship.evidence_id)
        .where(
            or_(EntityRelationship.from_entity_id == entity_id, EntityRelationship.to_entity_id == entity_id),
            Evidence.deleted_at.is_(None),
        )
        .limit(100)
    ).all()
    related: list[RelatedEntity] = []
    seen: set[str] = set()
    for relation in relationships:
        other_id = relation.to_entity_id if relation.from_entity_id == entity_id else relation.from_entity_id
        other = db.get(Entity, other_id)
        if not other or str(other.id) in seen:
            continue
        seen.add(str(other.id))
        related.append(
            RelatedEntity(
                id=other.id,
                type=other.type.value,
                value=other.value,
                relationship_type=relation.relationship_type,
                confidence=relation.confidence,
                evidence_id=relation.evidence_id,
            )
        )

    event_ids = select(EventEntity.event_id).where(EventEntity.entity_id == entity_id)
    events = list(
        db.scalars(
            select(TimelineEvent)
            .join(Evidence, Evidence.id == TimelineEvent.evidence_id)
            .where(TimelineEvent.id.in_(event_ids), Evidence.deleted_at.is_(None))
            .order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at, TimelineEvent.created_at)
            .limit(20)
        ).all()
    )
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

    return EntityDetail(
        **base.model_dump(),
        evidence=evidence_refs,
        related_entities=related,
        timeline_events=timeline,
    )


def build_graph(
    db: Session,
    *,
    types: str | None = None,
    q: str | None = None,
    include_events: bool = True,
    limit: int = 150,
) -> EntityGraph:
    type_values = _parse_types(types)
    stmt = select(Entity).where(Entity.type.in_(type_values), Entity.id.in_(_active_entity_ids()))
    if q and q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(Entity.value.ilike(needle), Entity.normalized_value.ilike(needle)))
    entities = list(db.scalars(stmt.order_by(Entity.mention_count.desc()).limit(limit)).all())
    entity_ids = [entity.id for entity in entities]

    linked_evidence = {
        entity_id: set()
        for entity_id in entity_ids
    }
    if entity_ids:
        for entity_id, evidence_id in db.execute(
            select(EvidenceEntity.entity_id, EvidenceEntity.evidence_id)
            .join(Evidence, Evidence.id == EvidenceEntity.evidence_id)
            .where(EvidenceEntity.entity_id.in_(entity_ids), Evidence.deleted_at.is_(None))
        ).all():
            linked_evidence.setdefault(entity_id, set()).add(evidence_id)

    nodes = [
        GraphNode(
            id=f"entity:{entity.id}",
            label=entity.value,
            kind=entity.type.value,
            sublabel=f"{entity.type.value.title()} · {entity.mention_count} mentions",
            confidence=entity.confidence,
            mention_count=entity.mention_count,
            evidence_ids=list(linked_evidence.get(entity.id, set())),
            person_id=entity.id if entity.type == EntityType.PERSON else None,
        )
        for entity in entities
    ]

    edges: list[GraphEdge] = []
    if entity_ids:
        relationships = db.scalars(
            select(EntityRelationship)
            .join(Evidence, Evidence.id == EntityRelationship.evidence_id)
            .where(
                EntityRelationship.from_entity_id.in_(entity_ids),
                EntityRelationship.to_entity_id.in_(entity_ids),
                Evidence.deleted_at.is_(None),
            )
            .limit(400)
        ).all()
        for relation in relationships:
            edges.append(
                GraphEdge(
                    id=f"rel:{relation.id}",
                    source=f"entity:{relation.from_entity_id}",
                    target=f"entity:{relation.to_entity_id}",
                    type=relation.relationship_type,
                    label=relation.relationship_type.replace("_", " "),
                    confidence=relation.confidence,
                    evidence_id=relation.evidence_id,
                    context=relation.context,
                )
            )

    if include_events and entity_ids:
        event_rows = db.execute(
            select(TimelineEvent, EventEntity.entity_id)
            .join(EventEntity, EventEntity.event_id == TimelineEvent.id)
            .join(Evidence, Evidence.id == TimelineEvent.evidence_id)
            .where(EventEntity.entity_id.in_(entity_ids), Evidence.deleted_at.is_(None))
            .order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at)
            .limit(80)
        ).all()
        added_events: set[uuid.UUID] = set()
        for event, entity_id in event_rows:
            node_id = f"event:{event.id}"
            if event.id not in added_events:
                nodes.append(
                    GraphNode(
                        id=node_id,
                        label=event.title,
                        kind="event",
                        sublabel=event.occurred_at_raw or event.category.value,
                        confidence=event.confidence,
                        evidence_ids=[event.evidence_id],
                    )
                )
                added_events.add(event.id)
            edges.append(
                GraphEdge(
                    id=f"event-link:{event.id}:{entity_id}",
                    source=node_id,
                    target=f"entity:{entity_id}",
                    type="referenced_in",
                    label="referenced in",
                    confidence=event.confidence,
                    evidence_id=event.evidence_id,
                )
            )

    stats = GraphStats(
        nodes=len(nodes),
        edges=len(edges),
        people=sum(1 for entity in entities if entity.type == EntityType.PERSON),
        organizations=sum(1 for entity in entities if entity.type == EntityType.ORGANIZATION),
    )
    return EntityGraph(nodes=nodes, edges=edges, stats=stats)
