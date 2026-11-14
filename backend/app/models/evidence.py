from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EvidenceStatus, FileType, IntegrityStatus, ProcessingStage
from app.utils.time import utcnow


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_filename: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(String(1200))
    mime_type: Mapped[str] = mapped_column(String(160))
    file_type: Mapped[FileType] = mapped_column(
        SAEnum(FileType, native_enum=False, length=16, values_callable=lambda e: [i.value for i in e])
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    phash: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(180), default="Upload")
    status: Mapped[EvidenceStatus] = mapped_column(
        SAEnum(EvidenceStatus, native_enum=False, length=16, values_callable=lambda e: [i.value for i in e]),
        default=EvidenceStatus.PENDING,
        index=True,
    )
    processing_stage: Mapped[ProcessingStage] = mapped_column(
        SAEnum(ProcessingStage, native_enum=False, length=32, values_callable=lambda e: [i.value for i in e]),
        default=ProcessingStage.QUEUED,
    )
    processing_progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    integrity_status: Mapped[IntegrityStatus] = mapped_column(
        SAEnum(IntegrityStatus, native_enum=False, length=16, values_callable=lambda e: [i.value for i in e]),
        default=IntegrityStatus.PENDING,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence.id"), nullable=True)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    uploaded_by = relationship("User", back_populates="evidence")
    duplicate_of = relationship("Evidence", remote_side=[id], uselist=False)
    extracted_content = relationship(
        "ExtractedContent", back_populates="evidence", cascade="all, delete-orphan", order_by="ExtractedContent.created_at"
    )
    entity_links = relationship("EvidenceEntity", back_populates="evidence", cascade="all, delete-orphan")
    entity_relationships = relationship("EntityRelationship", back_populates="evidence", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="evidence", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_evidence_sha_deleted", "sha256", "deleted_at"),
        Index("ix_evidence_status_deleted", "status", "deleted_at"),
    )
