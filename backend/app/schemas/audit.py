from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel


class AuditEntryOut(APIModel):
    id: int
    actor: str
    action: str
    target: str
    target_type: str
    target_id: str | None = None
    at: datetime
    ip: str | None = None
    result: str
    details: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str
    hash: str


class AuditPage(APIModel):
    items: list[AuditEntryOut]
    total: int
    limit: int
    offset: int
    chain_valid: bool


class AuditVerify(APIModel):
    valid: bool
    entries: int
    broken_at: int | None = None
    message: str
    checked_at: datetime
