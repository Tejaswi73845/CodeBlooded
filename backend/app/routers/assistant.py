from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import current_workspace
from app.models import Evidence, Workspace
from app.schemas.assistant import ChatRequest, ChatResponse, ReindexRequest, ReindexResponse
from app.services import rag_service
from app.services.assistant_service import answer_question
from app.services.audit_service import record_audit
from app.utils.http import actor_name, client_ip, user_agent
from app.utils.time import utcnow

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(current_workspace),
):
    response = answer_question(
        db,
        question=payload.question,
        evidence_ids=payload.evidence_ids,
        limit=payload.limit,
        workspace_id=workspace.id,
    )
    record_audit(
        db,
        actor=actor_name(request),
        action="Assistant queried",
        target_type="assistant",
        target_id=None,
        details={
            "question": payload.question[:500],
            "sources": [str(source.evidence_id) for source in response.sources],
            "insufficient": response.insufficient_evidence,
            "mode": response.mode,
            "retrievalMode": response.retrieval_mode,
        },
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=workspace.id,
    )
    return response


@router.post("/reindex", response_model=ReindexResponse)
def reindex(
    request: Request,
    payload: ReindexRequest | None = None,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(current_workspace),
):
    """Backfill chunking + embeddings for existing evidence (e.g. after enabling Gemini)."""
    evidence_ids = payload.evidence_ids if payload else []
    if not evidence_ids:
        evidence_ids = list(
            db.scalars(
                select(Evidence.id).where(
                    Evidence.deleted_at.is_(None),
                    Evidence.workspace_id == workspace.id,
                )
            ).all()
        )
    stats = rag_service.reindex(db, evidence_ids or None)
    record_audit(
        db,
        actor=actor_name(request),
        action="Retrieval index rebuilt",
        target_type="assistant",
        target_id=None,
        details={
            "evidence": stats.evidence,
            "chunks": stats.chunks,
            "embedded": stats.embedded,
            "failed": stats.failed,
            "model": stats.model,
            "errors": stats.errors[:3],
        },
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=workspace.id,
    )
    return ReindexResponse(
        evidence_indexed=stats.evidence,
        chunks=stats.chunks,
        embedded=stats.embedded,
        failed=stats.failed,
        embedding_model=stats.model or settings.gemini_embedding_model,
        dimensions=stats.dimensions,
        errors=stats.errors,
        generated_at=utcnow(),
    )
