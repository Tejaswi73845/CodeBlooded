from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AIServiceError
from app.models import DocumentChunk, Evidence, ExtractedContent
from app.models.enums import EvidenceStatus
from app.services.ai_service import ai_service
from app.services.chunking_service import chunk_content
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IndexStats:
    evidence: int = 0
    chunks: int = 0
    embedded: int = 0
    failed: int = 0
    model: str | None = None
    dimensions: int | None = None
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "IndexStats") -> None:
        self.evidence += other.evidence
        self.chunks += other.chunks
        self.embedded += other.embedded
        self.failed += other.failed
        self.errors.extend(other.errors)
        self.model = other.model or self.model
        self.dimensions = other.dimensions or self.dimensions


def index_evidence(db: Session, evidence: Evidence, *, embed: bool = True) -> IndexStats:
    contents = list(
        db.scalars(
            select(ExtractedContent)
            .where(ExtractedContent.evidence_id == evidence.id)
            .order_by(ExtractedContent.page_number, ExtractedContent.created_at)
        ).all()
    )
    db.execute(delete(DocumentChunk).where(DocumentChunk.evidence_id == evidence.id))
    db.commit()

    drafts = []
    for content in contents:
        drafts.extend(chunk_content(content))
    if not drafts:
        return IndexStats(evidence=1, failed=0, model=settings.gemini_embedding_model)

    chunks = [
        DocumentChunk(
            evidence_id=evidence.id,
            content_id=draft.content_id,
            chunk_index=draft.chunk_index,
            text=draft.text,
            content_kind=draft.content_kind,
            page_number=draft.page_number,
            timestamp_start=draft.timestamp_start,
            timestamp_end=draft.timestamp_end,
            content_hash=draft.content_hash,
            meta=draft.meta,
        )
        for draft in drafts
    ]
    db.add_all(chunks)
    db.commit()

    stats = IndexStats(
        evidence=1,
        chunks=len(chunks),
        model=settings.gemini_embedding_model,
    )
    if not embed or not ai_service.configured:
        if not ai_service.configured:
            stats.errors.append("Gemini embeddings are not configured; chunks support lexical retrieval only.")
        return stats

    try:
        result = ai_service.embed_texts([chunk.text for chunk in chunks], task_type="RETRIEVAL_DOCUMENT")
        for chunk, vector in zip(chunks, result.vectors, strict=True):
            chunk.embedding = vector
            chunk.embedding_model = result.model
            chunk.embedding_dim = len(vector)
        db.add_all(chunks)
        db.commit()
        stats.embedded = len(chunks)
        stats.model = result.model
        stats.dimensions = result.dimensions
    except AIServiceError as exc:
        logger.warning("RAG embedding failed for evidence %s: %s", evidence.id, exc)
        db.rollback()
        stats.failed = len(chunks)
        stats.errors.append(exc.message)
    except Exception as exc:  # noqa: BLE001 - indexing must never break evidence processing
        logger.exception("Unexpected RAG indexing failure for %s", evidence.id)
        db.rollback()
        stats.failed = len(chunks)
        stats.errors.append(f"Embedding failed: {exc}")
    return stats


def reindex(
    db: Session,
    evidence_ids: list[uuid.UUID] | None = None,
    *,
    embed: bool = True,
    limit: int = 200,
) -> IndexStats:
    stmt = select(Evidence).where(Evidence.deleted_at.is_(None))
    if evidence_ids:
        stmt = stmt.where(Evidence.id.in_(evidence_ids))
    rows = list(db.scalars(stmt.order_by(Evidence.uploaded_at.asc()).limit(limit)).all())
    total = IndexStats(model=settings.gemini_embedding_model)
    for evidence in rows:
        total.merge(index_evidence(db, evidence, embed=embed))
    return total


def ensure_index(db: Session, evidence_ids: list[uuid.UUID] | None = None, *, limit: int = 12) -> IndexStats:
    """Index completed evidence that has content but no chunks yet."""
    active = select(Evidence.id).where(Evidence.deleted_at.is_(None))
    if evidence_ids:
        active = active.where(Evidence.id.in_(evidence_ids))
    with_content = select(ExtractedContent.evidence_id).where(ExtractedContent.text.is_not(None))
    already_indexed = select(DocumentChunk.evidence_id)
    pending = list(
        db.scalars(
            active.where(Evidence.status == EvidenceStatus.COMPLETED)
            .where(Evidence.id.in_(with_content))
            .where(Evidence.id.not_in(already_indexed))
            .limit(limit)
        ).all()
    )
    total = IndexStats(model=settings.gemini_embedding_model)
    for evidence_id in pending:
        evidence = db.get(Evidence, evidence_id)
        if evidence:
            total.merge(index_evidence(db, evidence, embed=ai_service.configured))
    return total
