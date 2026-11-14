from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class WorkspaceOut(APIModel):
    id: uuid.UUID
    name: str
    is_default: bool = False
    evidence_count: int = 0
    created_at: datetime


class WorkspaceList(APIModel):
    items: list[WorkspaceOut]
    total: int


class WorkspaceCreate(APIModel):
    name: str = Field(min_length=1, max_length=160)


class WorkspaceUpdate(APIModel):
    name: str = Field(min_length=1, max_length=160)
