from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel


class ReportGenerateRequest(APIModel):
    title: str | None = Field(default=None, max_length=300)
    report_type: str = Field(default="incident", pattern="^(incident|chronology|integrity|relationships|custom)$")
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    include_ai_summary: bool = True
    actor: str | None = Field(default=None, max_length=160)


class ReportOut(APIModel):
    id: uuid.UUID
    title: str
    type: str
    status: str
    author: str
    created_at: datetime
    pages: int
    evidence_count: int
    generated_by: str
    model: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    markdown: str = ""


class ReportSummary(APIModel):
    id: uuid.UUID
    title: str
    type: str
    status: str
    author: str
    created_at: datetime
    pages: int
    evidence_count: int
    generated_by: str


class ReportPage(APIModel):
    items: list[ReportSummary]
    total: int
    limit: int
    offset: int
