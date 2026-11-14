from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import APIModel


class ChatRequest(APIModel):
    question: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=100,
        json_schema_extra={"example": []},
    )
    limit: int = Field(default=8, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class SourceRef(APIModel):
    evidence_id: uuid.UUID
    evidence_name: str
    file_type: str
    excerpt: str
    page_number: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    relevance: float = 0.0
    locator: str | None = None


class ChatResponse(APIModel):
    answer: str
    insufficient_evidence: bool = False
    sources: list[SourceRef] = Field(default_factory=list)
    mode: str = "extractive"
    model: str | None = None
    limitations: list[str] = Field(default_factory=list)
    retrieval_mode: str = "lexical"
    chunks_considered: int = 0
    generated_at: datetime


class ReindexRequest(APIModel):
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


class ReindexResponse(APIModel):
    evidence_indexed: int
    chunks: int
    embedded: int
    failed: int
    embedding_model: str
    dimensions: int | None = None
    errors: list[str] = Field(default_factory=list)
    generated_at: datetime
