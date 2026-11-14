from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.evidence import EvidenceSummary, TimelineBrief


class EntityEvidenceRef(APIModel):
    evidence_id: uuid.UUID
    evidence_name: str
    excerpt: str | None = None
    occurrence_count: int = 1
    page_number: int | None = None
    timestamp_start: float | None = None


class EntitySummary(APIModel):
    id: uuid.UUID
    type: str
    value: str
    normalized_value: str
    confidence: float
    source: str
    mention_count: int
    evidence_count: int = 0
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    first_seen_at: datetime
    last_seen_at: datetime
    meta: dict = Field(default_factory=dict)


class RelatedEntity(APIModel):
    id: uuid.UUID
    type: str
    value: str
    relationship_type: str
    confidence: float
    evidence_id: uuid.UUID | None = None


class EntityDetail(EntitySummary):
    evidence: list[EntityEvidenceRef] = Field(default_factory=list)
    related_entities: list[RelatedEntity] = Field(default_factory=list)
    timeline_events: list[TimelineBrief] = Field(default_factory=list)


class GraphNode(APIModel):
    id: str
    label: str
    kind: str
    sublabel: str | None = None
    confidence: float = 0.5
    mention_count: int = 0
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    person_id: uuid.UUID | None = None


class GraphEdge(APIModel):
    id: str
    source: str
    target: str
    type: str
    label: str | None = None
    confidence: float = 0.5
    evidence_id: uuid.UUID | None = None
    context: str | None = None


class GraphStats(APIModel):
    nodes: int
    edges: int
    people: int
    organizations: int


class EntityGraph(APIModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: GraphStats


class EntityPage(APIModel):
    items: list[EntitySummary]
    total: int
    limit: int
    offset: int


class EntityDetailEnvelope(EntityDetail):
    pass


__all__ = [
    "EntityDetail",
    "EntityDetailEnvelope",
    "EntityEvidenceRef",
    "EntityGraph",
    "EntityPage",
    "EntitySummary",
    "EvidenceSummary",
    "GraphEdge",
    "GraphNode",
    "GraphStats",
    "RelatedEntity",
    "TimelineBrief",
]
