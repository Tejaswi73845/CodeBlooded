from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AIServiceError
from app.models import DocumentChunk, Entity, Evidence
from app.models.enums import EvidenceStatus
from app.services.ai_service import ai_service
from app.utils.logging import get_logger
from app.utils.text import tokenize
from app.utils.time import format_duration

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    evidence: Evidence
    score: float
    vector_score: float = 0.0
    lexical_score: float = 0.0
    entity_boost: float = 0.0

    @property
    def locator(self) -> str | None:
        if self.chunk.page_number:
            return f"page {self.chunk.page_number}"
        if self.chunk.timestamp_start is not None:
            start = format_duration(self.chunk.timestamp_start)
            end = format_duration(self.chunk.timestamp_end)
            return f"{start}–{end}" if end else start
        return None


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    mode: str = "lexical"
    considered: int = 0
    limitations: list[str] = field(default_factory=list)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_left * norm_right)))


def lexical_score(text: str, tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    lowered = text.lower()
    hits = sum(min(lowered.count(token), 5) for token in tokens)
    return min(1.0, hits / (len(tokens) * 2.0))


def _entity_evidence_boost(db: Session, question: str, tokens: list[str]) -> set[uuid.UUID]:
    if not tokens:
        return set()
    conditions = [Entity.normalized_value.ilike(f"%{token}%") for token in tokens[:6]]
    conditions.extend(Entity.value.ilike(f"%{token}%") for token in tokens[:6])
    entities = db.scalars(select(Entity).where(or_(*conditions)).limit(50)).all()
    lowered = question.lower()
    boosted: set[uuid.UUID] = set()
    for entity in entities:
        if entity.normalized_value and entity.normalized_value in lowered:
            for link in entity.evidence_links:
                boosted.add(link.evidence_id)
        elif entity.value.lower() in lowered:
            for link in entity.evidence_links:
                boosted.add(link.evidence_id)
    return boosted


def retrieve(
    db: Session,
    question: str,
    *,
    evidence_ids: list[uuid.UUID] | None = None,
    limit: int = 8,
    broad: bool = False,
) -> RetrievalResult:
    settings_limit = max(1, min(limit, settings.assistant_max_sources))
    tokens = tokenize(question)
    result = RetrievalResult(considered=0)

    stmt = (
        select(DocumentChunk, Evidence)
        .join(Evidence, Evidence.id == DocumentChunk.evidence_id)
        .where(Evidence.deleted_at.is_(None), Evidence.status == EvidenceStatus.COMPLETED)
    )
    if evidence_ids:
        stmt = stmt.where(Evidence.id.in_(evidence_ids))
    rows = list(
        db.execute(stmt.order_by(DocumentChunk.created_at.desc()).limit(settings.rag_max_chunks)).all()
    )
    result.considered = len(rows)
    if not rows:
        result.mode = "empty-index"
        return result

    query_vector: list[float] | None = None
    if settings.rag_enabled and ai_service.embeddings_configured:
        try:
            query_vector = ai_service.embed_query(question)
        except AIServiceError as exc:
            logger.warning("Query embedding failed; using lexical retrieval: %s", exc)
            result.limitations.append(f"Vector search unavailable: {exc.message}")
    result.mode = "lexical"

    boosted_evidence = _entity_evidence_boost(db, question, tokens)
    scored: list[RetrievedChunk] = []
    used_vector = False
    for chunk, evidence in rows:
        vector = cosine_similarity(query_vector or [], chunk.embedding or [])
        lexical = lexical_score(chunk.text, tokens)
        entity = 1.0 if evidence.id in boosted_evidence else 0.0
        if query_vector and chunk.embedding:
            score = (
                settings.rag_vector_weight * vector
                + settings.rag_lexical_weight * lexical
                + settings.rag_entity_weight * entity
            )
            used_vector = True
        else:
            score = 0.85 * lexical + 0.15 * entity
        if vector == 0 and lexical == 0 and entity == 0 and not broad:
            continue
        # Reject unrelated questions that merely land near the vector centroid.
        if not broad and lexical == 0 and entity == 0 and vector < settings.rag_min_vector_match:
            continue
        if score < settings.rag_min_score and not broad:
            continue
        scored.append(
            RetrievedChunk(
                chunk=chunk,
                evidence=evidence,
                score=score,
                vector_score=vector,
                lexical_score=lexical,
                entity_boost=entity,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    selected: list[RetrievedChunk] = []
    seen_text: set[str] = set()
    per_evidence: dict[uuid.UUID, int] = {}
    for item in scored:
        fingerprint = " ".join(item.chunk.text.lower().split())[:280]
        if fingerprint in seen_text:
            continue
        if per_evidence.get(item.evidence.id, 0) >= 3:
            continue
        seen_text.add(fingerprint)
        per_evidence[item.evidence.id] = per_evidence.get(item.evidence.id, 0) + 1
        selected.append(item)
        if len(selected) >= settings_limit:
            break

    # For summary questions, ensure at least one passage from each source is available.
    if broad and len(selected) < settings_limit:
        selected_evidence = {item.evidence.id for item in selected}
        best_per_evidence: dict[uuid.UUID, RetrievedChunk] = {}
        for item in scored:
            best_per_evidence.setdefault(item.evidence.id, item)
        for evidence_id, item in best_per_evidence.items():
            if evidence_id in selected_evidence:
                continue
            selected.append(item)
            selected_evidence.add(evidence_id)
            if len(selected) >= settings_limit:
                break

    result.chunks = selected[:settings_limit]
    if selected:
        result.mode = "hybrid" if used_vector else "lexical"
    return result
