from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EntityType
from app.utils.time import utcnow


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, native_enum=False, length=24, values_callable=lambda e: [i.value for i in e]),
        index=True,
    )
    value: Mapped[str] = mapped_column(String(512))
    normalized_value: Mapped[str] = mapped_column(String(512), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(40), default="regex")
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    evidence_links = relationship("EvidenceEntity", back_populates="entity", cascade="all, delete-orphan")
    outgoing_relationships = relationship(
        "EntityRelationship",
        foreign_keys="EntityRelationship.from_entity_id",
        back_populates="from_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "EntityRelationship",
        foreign_keys="EntityRelationship.to_entity_id",
        back_populates="to_entity",
        cascade="all, delete-orphan",
    )
    event_links = relationship("EventEntity", back_populates="entity", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("type", "normalized_value", name="uq_entity_type_normalized"),
        Index("ix_entity_type_mentions", "type", "mention_count"),
    )


class EvidenceEntity(Base):
    __tablename__ = "evidence_entities"

    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    evidence = relationship("Evidence", back_populates="entity_links")
    entity = relationship("Entity", back_populates="evidence_links")


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    from_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    to_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=True, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(64), default="mentioned_together")
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    from_entity = relationship("Entity", foreign_keys=[from_entity_id], back_populates="outgoing_relationships")
    to_entity = relationship("Entity", foreign_keys=[to_entity_id], back_populates="incoming_relationships")
    evidence = relationship("Evidence", back_populates="entity_relationships")


class EventEntity(Base):
    __tablename__ = "event_entities"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("timeline_events.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str | None] = mapped_column(String(40), nullable=True)

    event = relationship("TimelineEvent", back_populates="entity_links")
    entity = relationship("Entity", back_populates="event_links")
