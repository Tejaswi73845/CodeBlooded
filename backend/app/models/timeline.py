from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EventCategory
from app.utils.time import utcnow


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    occurred_at_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time_uncertain: Mapped[bool] = mapped_column(Boolean, default=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[EventCategory] = mapped_column(
        SAEnum(EventCategory, native_enum=False, length=24, values_callable=lambda e: [i.value for i in e]),
        default=EventCategory.OTHER,
        index=True,
    )
    severity: Mapped[str] = mapped_column(String(16), default="info")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_source: Mapped[str] = mapped_column(String(32), default="regex")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    evidence = relationship("Evidence", back_populates="timeline_events")
    entity_links = relationship("EventEntity", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_timeline_time_category", "occurred_at", "category"),)
