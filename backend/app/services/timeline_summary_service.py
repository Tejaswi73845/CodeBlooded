from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AIServiceError
from app.models import Evidence, TimelineEvent
from app.schemas.timeline import TimelineSummaryItem
from app.services.ai_service import ai_service
from app.utils.logging import get_logger
from app.utils.narrative import sanitize_summary
from app.utils.text import truncate
from app.utils.time import utcnow

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You summarise reconstructed timeline events for a forensic investigator. "
    "Each event card already displays its own date, time and location, so do not repeat them "
    "unless the source states them verbatim and they are essential to the meaning. "
    "For each event id write ONE factual sentence (max 30 words) about who did what, to whom, "
    "and why it matters: the request, demand, payment, threat or decision. "
    "Describe the substance, not the file type, and never transcribe email headers, "
    "Message-IDs, IP addresses or angle-bracket addresses. "
    "Never invent facts. Return a JSON object mapping each id string to its sentence."
)


def summarize_events(
    db: Session,
    event_ids: list[uuid.UUID],
    workspace_id: uuid.UUID,
    *,
    refresh: bool = False,
    context: str | None = None,
) -> list[TimelineSummaryItem]:
    if not event_ids:
        return []

    events = list(
        db.scalars(
            select(TimelineEvent)
            .join(Evidence, Evidence.id == TimelineEvent.evidence_id)
            .where(
                TimelineEvent.id.in_(event_ids),
                Evidence.deleted_at.is_(None),
                Evidence.workspace_id == workspace_id,
            )
        ).all()
    )
    if not events:
        return []

    resolved: dict[uuid.UUID, dict[str, str]] = {}
    pending: list[TimelineEvent] = []
    for event in events:
        cached = _cached(event)
        if cached and not refresh:
            resolved[event.id] = cached
        else:
            pending.append(event)

    groups: dict[uuid.UUID, list[TimelineEvent]] = {}
    for event in pending:
        groups.setdefault(event.evidence_id, []).append(event)

    for evidence_id, group in groups.items():
        generated, mode = _summarize_group(db, evidence_id, group, context=context)
        for event in group:
            summary = generated.get(str(event.id))
            event_mode = "ai" if summary else "extractive"
            if not summary:
                summary = truncate(event.description or event.title, 260)
            event.meta = {
                **(event.meta or {}),
                "aiSummary": {
                    "summary": summary,
                    "mode": event_mode,
                    "generatedAt": utcnow().isoformat(),
                },
            }
            db.add(event)
            resolved[event.id] = {"summary": summary, "mode": event_mode}
    db.commit()

    return [
        TimelineSummaryItem(
            id=event.id,
            summary=resolved.get(event.id, {}).get("summary") or truncate(event.description, 260),
            mode=resolved.get(event.id, {}).get("mode") or "extractive",
        )
        for event in events
    ]


def _cached(event: TimelineEvent) -> dict[str, str] | None:
    cached = (event.meta or {}).get("aiSummary")
    if isinstance(cached, dict) and cached.get("summary"):
        return {
            "summary": str(cached["summary"]),
            "mode": str(cached.get("mode") or "ai"),
        }
    return None


def _summarize_group(
    db: Session,
    evidence_id: uuid.UUID,
    events: list[TimelineEvent],
    *,
    context: str | None = None,
) -> tuple[dict[str, str], str]:
    if not ai_service.configured:
        return {}, "extractive"
    evidence = db.get(Evidence, evidence_id)
    blocks: list[str] = []
    for event in events[:40]:
        when = event.occurred_at_raw or (
            event.occurred_at.isoformat() if event.occurred_at else "time unknown"
        )
        blocks.append(
            f"id: {event.id}\n"
            f"title: {event.title}\n"
            f"description: {truncate(event.description, 320)}\n"
            f"at: {when}\n"
            f"location: {(event.meta or {}).get('location') or 'not recorded'}\n"
            f"evidence: {evidence.original_filename if evidence else 'unknown'}\n"
            f"excerpt: {truncate(event.source_excerpt or '', 320)}"
        )
    prompt = "Summarise each event below.\n\n" + "\n---\n".join(blocks)
    if context and context.strip():
        prompt = (
            "INVESTIGATOR CONTEXT / CORRECTION (authoritative for interpretation; "
            "use it to disambiguate or correct the events, but never invent beyond it):\n"
            f"{context.strip()[:2000]}\n\n{prompt}"
        )
    try:
        result = ai_service.generate_json(prompt, system=SYSTEM_PROMPT, temperature=0.1)
    except AIServiceError as exc:
        logger.warning("Timeline summary generation failed for evidence %s: %s", evidence_id, exc)
        return {}, "extractive"

    cleaned: dict[str, str] = {}
    by_id = {str(event.id): event for event in events}
    for key, value in result.items():
        if isinstance(value, str) and value.strip():
            event = by_id.get(str(key))
            summary = value.strip()
            if event is not None:
                summary = sanitize_summary(summary, event.occurred_at_raw)
            cleaned[str(key)] = summary or value.strip()
    return cleaned, "ai"
