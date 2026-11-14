from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel


class ExtractedContentOut(APIModel):
    id: uuid.UUID
    kind: str
    text: str
    language: str | None = None
    confidence: float | None = None
    page_number: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class EntityBrief(APIModel):
    id: uuid.UUID
    type: str
    value: str
    normalized_value: str
    confidence: float
    mention_count: int


class TimelineBrief(APIModel):
    id: uuid.UUID
    at: datetime | None = None
    at_raw: str | None = None
    time_uncertain: bool = True
    title: str
    category: str
    confidence: float
    evidence_id: uuid.UUID
    page_number: int | None = None
    source_timestamp: float | None = None


class EvidenceSummary(APIModel):
    id: uuid.UUID
    reference: str
    name: str
    type: str
    mime: str
    size: int
    uploaded_at: datetime
    uploaded_by: str
    status: str
    stage: str
    progress: int
    source: str
    hash: str
    integrity: str
    person_ids: list[uuid.UUID] = Field(default_factory=list)
    event_ids: list[uuid.UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    duration: float | None = None
    pages: int | None = None
    note: str | None = None
    preview: str | None = None
    duplicate_of: uuid.UUID | None = None
    error: str | None = None
    verified_at: datetime | None = None
    # Capture metadata recorded by the analyst at upload time.
    occurred_at: datetime | None = None
    location: str | None = None
    persons: list[str] = Field(default_factory=list)
    capture_note: str | None = None
    capture_detected: list[str] = Field(default_factory=list)
    needs_review: bool = False
    missing_capture: list[str] = Field(default_factory=list)


class DuplicateWarning(APIModel):
    evidence_id: uuid.UUID
    reference: str
    name: str
    sha256: str
    similarity: float = 1.0
    kind: str = "exact"


class CaptureUpdate(APIModel):
    date: str | None = Field(default=None, max_length=32)
    time: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=300)
    persons: list[str] = Field(default_factory=list, max_length=20)
    note: str | None = Field(default=None, max_length=2000)


class EvidenceAiSummary(APIModel):
    evidence_id: uuid.UUID
    evidence_name: str
    summary: str
    mode: str = "ai"
    model: str | None = None
    cached: bool = False
    generated_at: datetime
    limitations: list[str] = Field(default_factory=list)


class VaultVerifyResponse(APIModel):
    checked: int
    verified: int
    mismatch: int
    failed: int
    chain_valid: bool
    broken_at: int | None = None
    checked_at: datetime
    mismatched_ids: list[uuid.UUID] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class UploadError(APIModel):
    filename: str
    error: str


class UploadResponse(APIModel):
    items: list[EvidenceSummary]
    duplicates: list[DuplicateWarning]
    errors: list[UploadError]
    accepted: int


class StatusResponse(APIModel):
    id: uuid.UUID
    status: str
    stage: str
    progress: int
    error: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    integrity: str
    verified_at: datetime | None = None


class EvidenceDetail(EvidenceSummary):
    metadata: dict[str, Any] = Field(default_factory=dict)
    extracted_content: list[ExtractedContentOut] = Field(default_factory=list)
    entities: list[EntityBrief] = Field(default_factory=list)
    timeline_events: list[TimelineBrief] = Field(default_factory=list)
    duplicates: list[DuplicateWarning] = Field(default_factory=list)


class EvidencePage(APIModel):
    items: list[EvidenceSummary]
    total: int
    limit: int
    offset: int
    counts: dict[str, int] = Field(default_factory=dict)
