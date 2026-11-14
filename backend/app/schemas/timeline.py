from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class TimelinePerson(APIModel):
    id: uuid.UUID
    name: str
    confidence: float = 0.5


class TimelineEventOut(APIModel):
    id: uuid.UUID
    at: datetime | None = None
    at_raw: str | None = None
    time_uncertain: bool = True
    title: str
    description: str
    category: str
    severity: str
    confidence: float
    evidence_id: uuid.UUID
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_name: str
    evidence_type: str
    person_ids: list[uuid.UUID] = Field(default_factory=list)
    people: list[TimelinePerson] = Field(default_factory=list)
    page_number: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    source_excerpt: str | None = None
    location: str | None = None
    extraction_source: str = "regex"


class TimelinePage(APIModel):
    items: list[TimelineEventOut]
    total: int
    limit: int
    offset: int
    earliest: datetime | None = None
    latest: datetime | None = None
    uncertain_count: int = 0
