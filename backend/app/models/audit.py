from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import AuditResult
from app.utils.time import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(160), default="system")
    action: Mapped[str] = mapped_column(String(120))
    target_type: Mapped[str] = mapped_column(String(60), default="system")
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    result: Mapped[AuditResult] = mapped_column(
        SAEnum(AuditResult, native_enum=False, length=16, values_callable=lambda e: [i.value for i in e]),
        default=AuditResult.SUCCESS,
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    previous_hash: Mapped[str] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    __table_args__ = (Index("ix_audit_target", "target_type", "target_id"),)
