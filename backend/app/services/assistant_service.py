from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import (
    AIConfigurationError,
    AIInvalidRequest,
    AIInvalidResponse,
    AISafetyBlocked,
    AIServiceUnavailable,
)
from app.models import Evidence, TimelineEvent
from app.schemas.assistant import ChatResponse, SourceRef
from app.services import rag_service, retrieval_service
from app.services.ai_service import ai_service
from app.services.retrieval_service import RetrievalResult, RetrievedChunk
from app.utils.logging import get_logger
from app.utils.text import excerpt_around, tokenize, truncate
from app.utils.time import utcnow

logger = get_logger(__name__)

SUMMARY_INTENT = (
    "summar", "overview", "brief", "incident report", "list all", "mentioned most", "most frequently",
    "identify inconsistencies", "contradiction", "who was involved", "who is involved",
    "who are the people", "how many people", "how many events",
)

METADATA_PHRASES = (
    "latest evidence", "latest file", "latest upload", "latest document", "latest item",
    "most recent evidence", "most recent file", "most recent upload", "most recent document",
    "newest evidence", "newest file", "newest upload", "newest document",
    "recent evidence", "recent uploads", "recent files",
    "what have i uploaded", "what did i upload", "what evidence do i have",
    "list evidence", "list all evidence", "list my evidence",
    "how many evidence", "how many files", "how many documents", "how many uploads",
    "whats my latest", "what's my latest", "what is my latest",
)


def _is_metadata_question(question: str) -> bool:
    lowered = " ".join(question.lower().split())
    if not any(term in lowered for term in ("evidence", "file", "upload", "document", "item")):
        return False
    return any(phrase in lowered for phrase in METADATA_PHRASES)


def answer_question(
    db: Session,
    *,
    question: str,
    evidence_ids: list[uuid.UUID] | None = None,
    limit: int = 8,
    workspace_id: uuid.UUID | None = None,
) -> ChatResponse:
    limit = max(1, min(limit, settings.assistant_max_sources))
    tokens = tokenize(question)
    is_summary = any(phrase in question.lower() for phrase in SUMMARY_INTENT) or not tokens

    base = select(Evidence).where(Evidence.deleted_at.is_(None))
    if workspace_id is not None:
        base = base.where(Evidence.workspace_id == workspace_id)
    if evidence_ids:
        base = base.where(Evidence.id.in_(evidence_ids))
    evidence_rows = list(db.scalars(base).all())
    if not evidence_rows:
        total_active = int(
            db.scalar(select(func.count(Evidence.id)).where(Evidence.deleted_at.is_(None))) or 0
        )
        if evidence_ids and total_active:
            requested = ", ".join(str(item) for item in evidence_ids[:3])
            return _insufficient(
                "None of the supplied evidence IDs match active evidence in this workspace.",
                "Check the IDs or omit evidenceIds to search all evidence.",
                limitations=[f"Requested evidenceIds: {requested}"],
                retrieval_mode="metadata",
            )
        return _insufficient(
            "There is no preserved evidence available for this workspace yet. Upload and process evidence first.",
            "No active evidence records matched the request.",
            retrieval_mode="metadata",
        )

    if _is_metadata_question(question):
        return _metadata_answer(evidence_rows, question, limit)

    active_ids = [row.id for row in evidence_rows]

    # Backfill the index for evidence processed before RAG was enabled.
    index_stats = rag_service.ensure_index(db, active_ids)
    if index_stats.errors:
        logger.warning("RAG backfill reported: %s", index_stats.errors[:2])

    retrieval = retrieval_service.retrieve(
        db,
        question,
        evidence_ids=active_ids,
        limit=limit,
        broad=is_summary,
    )
    timeline_events = _timeline_context(db, question, active_ids, tokens, allow_fallback=is_summary)

    if not retrieval.chunks:
        limitations = list(retrieval.limitations)
        if index_stats.errors:
            limitations.append(index_stats.errors[0])
        return _insufficient(
            "The preserved evidence does not contain enough information to answer this question.",
            "No relevant indexed evidence passages were found.",
            limitations=limitations,
            retrieval_mode=retrieval.mode,
            considered=retrieval.considered,
        )

    sources = [
        SourceRef(
            evidence_id=item.evidence.id,
            evidence_name=item.evidence.original_filename,
            file_type=item.evidence.file_type.value,
            excerpt=truncate(_source_excerpt(item.chunk.text, tokens), 700),
            page_number=item.chunk.page_number,
            timestamp_start=item.chunk.timestamp_start,
            timestamp_end=item.chunk.timestamp_end,
            relevance=round(min(1.0, item.score), 3),
            locator=item.locator,
        )
        for item in retrieval.chunks
    ]

    if not ai_service.configured:
        return _extractive_answer(
            retrieval.chunks,
            sources,
            timeline_events,
            reason="GEMINI_API_KEY is not configured; no AI interpretation was performed.",
            retrieval=retrieval,
        )

    try:
        return _gemini_answer(question, retrieval.chunks, sources, timeline_events, retrieval)
    except (AIServiceUnavailable, AIConfigurationError, AIInvalidRequest, AISafetyBlocked) as exc:
        # Provider connectivity, billing/quota, model-availability or safety problems
        # degrade to verbatim evidence excerpts rather than failing the question.
        logger.warning("AI provider unavailable; using extractive fallback: %s", exc)
        response = _extractive_answer(
            retrieval.chunks,
            sources,
            timeline_events,
            reason=f"The AI provider is unavailable ({truncate(exc.message, 180)}); showing verbatim evidence excerpts.",
            retrieval=retrieval,
        )
        return response


def _metadata_answer(evidence_rows: list[Evidence], question: str, limit: int) -> ChatResponse:
    lowered = " ".join(question.lower().split())
    singular = any(
        phrase in lowered for phrase in ("latest", "most recent", "newest", "last uploaded")
    ) and not any(phrase in lowered for phrase in ("list", "all", "how many", "recent evidence", "recent uploads"))
    ordered = sorted(evidence_rows, key=lambda item: item.uploaded_at, reverse=True)
    selected = ordered[: max(1, limit)] if not singular else ordered[:1]

    sources = [
        SourceRef(
            evidence_id=item.id,
            evidence_name=item.original_filename,
            file_type=item.file_type.value,
            excerpt=(
                f"Uploaded {_uploaded_label(item)} · {item.file_type.value} · {_size_label(item.size_bytes)} · "
                f"status {item.status.value} · integrity {item.integrity_status.value}"
            ),
            relevance=1.0,
            locator=_uploaded_label(item),
        )
        for item in selected
    ]
    if singular:
        item = selected[0]
        answer = (
            f"The latest active evidence item is `{item.original_filename}`, uploaded {_uploaded_label(item)} [S1].\n\n"
            f"{item.file_type.value.title()} · {_size_label(item.size_bytes)} · status {item.status.value} · "
            f"integrity {item.integrity_status.value}."
        )
    else:
        lines = [f"You have **{len(ordered)} active evidence item(s)**. The most recent are:"]
        for index, item in enumerate(selected, start=1):
            lines.append(
                f"• `{item.original_filename}` — uploaded {_uploaded_label(item)} · "
                f"{item.file_type.value} · {_size_label(item.size_bytes)} · {item.status.value} [S{index}]"
            )
        answer = "\n".join(lines)
    return ChatResponse(
        answer=answer,
        insufficient_evidence=False,
        sources=sources,
        mode="metadata",
        model=None,
        limitations=[],
        generated_at=utcnow(),
        retrieval_mode="metadata",
        chunks_considered=0,
    )


def _uploaded_label(evidence: Evidence) -> str:
    return evidence.uploaded_at.strftime("%d %b %Y, %H:%M UTC")


def _size_label(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _timeline_context(
    db: Session,
    question: str,
    evidence_ids: list[uuid.UUID],
    tokens: list[str],
    allow_fallback: bool = False,
) -> list[TimelineEvent]:
    stmt = select(TimelineEvent).where(TimelineEvent.evidence_id.in_(evidence_ids))
    if tokens:
        conditions = [
            TimelineEvent.title.ilike(f"%{token}%")
            for token in tokens[:5]
        ] + [
            TimelineEvent.description.ilike(f"%{token}%")
            for token in tokens[:5]
        ]
        stmt = stmt.where(or_(*conditions))
    events = list(
        db.scalars(
            stmt.order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at, TimelineEvent.created_at).limit(12)
        ).all()
    )
    if not events and allow_fallback:
        events = list(
            db.scalars(
                select(TimelineEvent)
                .where(TimelineEvent.evidence_id.in_(evidence_ids))
                .order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at.desc())
                .limit(8)
            ).all()
        )
    return events


def _source_excerpt(text: str, tokens: list[str]) -> str:
    for token in tokens:
        if token in text.lower():
            return excerpt_around(text, token, 260)
    return excerpt_around(text, "", 300)


def _gemini_answer(
    question: str,
    chunks: list[RetrievedChunk],
    sources: list[SourceRef],
    timeline_events: list[TimelineEvent],
    retrieval: RetrievalResult,
) -> ChatResponse:
    context_parts: list[str] = []
    used_chars = 0
    budget = settings.max_text_chars_for_ai
    for index, item in enumerate(chunks, start=1):
        block = (
            f"SOURCE S{index}\n"
            f"evidence_id: {item.evidence.id}\n"
            f"evidence_name: {item.evidence.original_filename}\n"
            f"locator: {item.locator or 'document'}\n"
            f"text: {item.chunk.text}\n"
        )
        if used_chars + len(block) > budget:
            block = block[: max(0, budget - used_chars)]
        context_parts.append(block)
        used_chars += len(block)
        if used_chars >= budget:
            break

    timeline_block = "\n".join(
        f"- {event.occurred_at.isoformat() if event.occurred_at else 'time unknown'} | "
        f"{event.occurred_at_raw or 'no raw timestamp'} | {event.title} | evidence {event.evidence_id}"
        for event in timeline_events
    )
    system = (
        "You are a forensic evidence assistant using retrieved evidence passages. Answer ONLY from the supplied sources. "
        "Cite every factual claim with the source marker, e.g. [S1]. Clearly label any inference as an inference. "
        "Never invent names, dates, numbers, events or evidence. If the sources do not answer the question, say so. "
        "Distinguish extracted fact from interpretation and preserve uncertainty. Return JSON only."
    )
    retrieval_note = (
        "Retrieval mode: hybrid vector + lexical + entity search."
        if retrieval.mode == "hybrid"
        else "Retrieval mode: lexical (vector search unavailable)."
    )
    prompt = (
        f"INVESTIGATOR QUESTION: {question}\n\n"
        f"{retrieval_note}\n\n"
        f"RETRIEVED EVIDENCE PASSAGES:\n{''.join(context_parts)}\n\n"
        f"TIMELINE FACTS (derived from the same evidence):\n{timeline_block or 'No dated events matched.'}\n\n"
        "Return JSON with keys: answer (string, with [S#] citations), used_sources (array of integers), "
        "insufficient_evidence (boolean), limitations (array of short strings). "
        "Keep the answer under 450 words. "
        "If the sources cannot support an answer, set insufficient_evidence=true and explain what is missing. "
        "Do not use any source number not listed above."
    )
    result = ai_service.generate_json(prompt, system=system, temperature=0.15)
    answer_text = str(result.get("answer", "")).strip()
    if not answer_text:
        raise AIInvalidResponse("Gemini returned an empty answer.")
    insufficient = bool(result.get("insufficient_evidence", False))
    limitations = [str(item) for item in result.get("limitations", []) if item][:5]
    limitations.extend(retrieval.limitations)
    used: list[int] = []
    for item in result.get("used_sources", []):
        try:
            index = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= index <= len(sources) and index not in used:
            used.append(index)
    if not used and not insufficient:
        limitations.append("The model did not map its answer to a source; verify the cited evidence manually.")
        used = list(range(1, min(len(sources), 3) + 1))
    chosen_sources = [sources[index - 1] for index in used]
    if insufficient:
        chosen_sources = []
    return ChatResponse(
        answer=answer_text,
        insufficient_evidence=insufficient,
        sources=chosen_sources,
        mode="gemini",
        model=ai_service.model,
        limitations=limitations,
        generated_at=utcnow(),
        retrieval_mode=retrieval.mode,
        chunks_considered=retrieval.considered,
    )


def _extractive_answer(
    chunks: list[RetrievedChunk],
    sources: list[SourceRef],
    timeline_events: list[TimelineEvent],
    *,
    reason: str,
    retrieval: RetrievalResult,
) -> ChatResponse:
    if not chunks:
        return _insufficient(
            "The preserved evidence does not contain enough information to answer this question.",
            "No relevant indexed evidence passages were found.",
            limitations=[reason],
            retrieval_mode=retrieval.mode,
            considered=retrieval.considered,
        )
    lines: list[str] = ["**AI synthesis is unavailable, so this is an extractive summary of preserved text.**"]
    lines.append("Retrieved evidence")
    for index, source in enumerate(sources, start=1):
        location = f" · {source.locator}" if source.locator else ""
        lines.append(
            f"• **{source.evidence_name}**{location} — {truncate(source.excerpt, 420)} [S{index}]"
        )
    if timeline_events:
        lines.append("\n**Dated events in the preserved record**")
        for event in timeline_events[:6]:
            when = event.occurred_at_raw or (event.occurred_at.isoformat() if event.occurred_at else "time unknown")
            uncertain = " (time uncertain)" if event.time_uncertain else ""
            lines.append(f"• {when}{uncertain} — {event.title} — {str(event.evidence_id)}")
    lines.append("\nThese are verbatim extracts, not investigative conclusions.")
    return ChatResponse(
        answer="\n".join(lines),
        insufficient_evidence=False,
        sources=sources,
        mode="extractive",
        model=None,
        limitations=[reason, *retrieval.limitations],
        generated_at=utcnow(),
        retrieval_mode=retrieval.mode,
        chunks_considered=retrieval.considered,
    )


def _insufficient(
    answer: str,
    limitation: str,
    *,
    limitations: list[str] | None = None,
    retrieval_mode: str = "lexical",
    considered: int = 0,
) -> ChatResponse:
    return ChatResponse(
        answer=answer,
        insufficient_evidence=True,
        sources=[],
        mode="insufficient",
        model=None,
        limitations=[limitation, *(limitations or [])],
        generated_at=utcnow(),
        retrieval_mode=retrieval_mode,
        chunks_considered=considered,
    )
