from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Entity, EventEntity, Evidence, EvidenceEntity, ExtractedContent, TimelineEvent
from app.models.enums import ContentKind, EntityType, EventCategory
from app.services.entity_service import EventCandidate
from app.utils.logging import get_logger
from app.utils.text import clean_text, split_sentences, truncate
from app.utils.time import find_date_expressions, parse_event_datetime

logger = get_logger(__name__)


@dataclass
class TimelineBuildResult:
    created: int
    uncertain: int
    source: str


def build_timeline_for_evidence(
    db: Session,
    evidence: Evidence,
    contents: list[ExtractedContent],
    ai_events: list[EventCandidate] | None = None,
) -> TimelineBuildResult:
    candidates: list[EventCandidate] = list(ai_events or [])
    # Supplement only dates the primary extraction did not cover. This prevents the same
    # dated fact appearing twice because Gemini and the deterministic pass both saw it.
    covered_times = {event.occurred_at for event in candidates if event.occurred_at is not None}
    covered_raw = {event.date_raw.strip().lower() for event in candidates if event.date_raw}
    for supplemental in _supplemental_events(contents):
        if supplemental.occurred_at is not None and supplemental.occurred_at in covered_times:
            continue
        if supplemental.date_raw and supplemental.date_raw.strip().lower() in covered_raw:
            continue
        candidates.append(supplemental)
        if supplemental.occurred_at is not None:
            covered_times.add(supplemental.occurred_at)
        if supplemental.date_raw:
            covered_raw.add(supplemental.date_raw.strip().lower())

    existing_events = _existing(db, evidence)
    existing_pairs = {
        (event.occurred_at_raw, (event.source_excerpt or "").strip().lower()[:100])
        for event in existing_events
    }
    existing_titles = {(event.title.lower(), event.occurred_at_raw or "") for event in existing_events}
    created = 0
    uncertain = 0
    for candidate in candidates[:60]:
        if not candidate.title.strip():
            continue
        pair = (candidate.date_raw, (candidate.excerpt or "").strip().lower()[:100])
        title_key = (candidate.title.lower()[:160], candidate.date_raw or "")
        if pair in existing_pairs or title_key in existing_titles:
            continue
        if candidate.occurred_at is None and not candidate.date_raw:
            # No timestamp is acceptable, but only when the sentence still describes an event.
            if len(candidate.description) < 40:
                continue
        existing_pairs.add(pair)
        existing_titles.add(title_key)

        timestamp_start, timestamp_end = _resolve_timestamp(contents, candidate)
        event = TimelineEvent(
            evidence_id=evidence.id,
            occurred_at=candidate.occurred_at,
            occurred_at_raw=candidate.date_raw,
            time_uncertain=candidate.time_uncertain,
            title=truncate(candidate.title, 250),
            description=truncate(candidate.description, 1200),
            category=candidate.category,
            severity=candidate.severity or _severity(candidate),
            confidence=candidate.confidence,
            page_number=candidate.page_number,
            source_timestamp=timestamp_start,
            source_excerpt=candidate.excerpt,
            extraction_source=candidate.source,
            meta={
                "timestampEnd": timestamp_end,
                "timeUncertain": candidate.time_uncertain,
            },
        )
        db.add(event)
        db.flush()
        _link_entities(db, evidence, event)
        created += 1
        if candidate.time_uncertain:
            uncertain += 1
    db.commit()
    logger.info("Timeline: %s events (%s uncertain) for %s", created, uncertain, evidence.id)
    return TimelineBuildResult(created=created, uncertain=uncertain, source="gemini" if ai_events else "deterministic")


def _existing(db: Session, evidence: Evidence) -> list[TimelineEvent]:
    return list(db.scalars(select(TimelineEvent).where(TimelineEvent.evidence_id == evidence.id)).all())


def clear_timeline(db: Session, evidence_id) -> None:
    db.execute(delete(TimelineEvent).where(TimelineEvent.evidence_id == evidence_id))
    db.commit()


def _supplemental_events(contents: list[ExtractedContent]) -> list[EventCandidate]:
    candidates: list[EventCandidate] = []
    for content in contents:
        if not content.text.strip():
            continue
        for sentence in split_sentences(content.text):
            dates = find_date_expressions(sentence)
            if not dates:
                continue
            raw = dates[0]
            occurred_at, uncertain = parse_event_datetime(raw)
            title = sentence
            for found in dates:
                title = title.replace(found, " ")
            title = re.sub(r"^(?:on|at|by|dated|the)\s+", "", title.strip(), flags=re.I)
            title = re.sub(r"\s+", " ", title).strip(" ,.;:-")
            if len(title) < 12:
                title = sentence
            candidates.append(
                EventCandidate(
                    title=truncate(title, 110),
                    description=truncate(sentence, 900),
                    date_raw=raw,
                    occurred_at=occurred_at,
                    time_uncertain=uncertain,
                    category=_categorize(sentence),
                    confidence=0.55 if uncertain else 0.65,
                    excerpt=truncate(sentence, 500),
                    page_number=content.page_number,
                    timestamp_start=content.timestamp_start,
                    source="regex_supplement",
                )
            )
        if len(candidates) >= 40:
            break
    return candidates


def _categorize(text: str) -> EventCategory:
    lowered = text.lower()
    if any(w in lowered for w in ("transfer", "payment", "₹", "inr", "bank", "invoice", "amount", "utr")):
        return EventCategory.FINANCIAL
    if any(w in lowered for w in ("message", "whatsapp", "email", "call", "chat", "dm", "threat")):
        return EventCategory.COMMUNICATION
    if any(w in lowered for w in ("cctv", "camera", "entered", "exited", "parking", "meeting", "visited")):
        return EventCategory.PHYSICAL
    if any(w in lowered for w in ("filed", "court", "interview", "counsel", "legal", "statement")):
        return EventCategory.LEGAL
    if any(w in lowered for w in ("login", "device", "export", "hash", "metadata", "server")):
        return EventCategory.DIGITAL
    return EventCategory.OTHER


def _severity(candidate: EventCandidate) -> str:
    text = f"{candidate.title} {candidate.description}".lower()
    if any(w in text for w in ("threat", "harm", "fraud", "unauthorised", "unauthorized", "transferred", "breach")):
        return "critical"
    if candidate.time_uncertain or any(w in text for w in ("failed", "missing", "mismatch", "unverified")):
        return "warning"
    return "info"


def _resolve_timestamp(contents: list[ExtractedContent], candidate: EventCandidate) -> tuple[float | None, float | None]:
    if candidate.timestamp_start is not None:
        return candidate.timestamp_start, None
    excerpt = (candidate.excerpt or candidate.description).lower()
    for content in contents:
        if content.kind == ContentKind.TRANSCRIPT and content.meta.get("segments"):
            for segment in content.meta["segments"]:
                text = clean_text(str(segment.get("text", ""))).lower()
                if text and (text in excerpt or excerpt[:30] in text):
                    return float(segment.get("start", 0)), float(segment.get("end", 0))
        if content.kind == ContentKind.FRAME_OCR and content.timestamp_start is not None:
            if excerpt[:25] and excerpt[:25] in clean_text(content.text).lower():
                return content.timestamp_start, content.timestamp_end
    return None, None


def _link_entities(db: Session, evidence: Evidence, event: TimelineEvent) -> None:
    haystack = f"{event.title} {event.description} {event.source_excerpt or ''}".lower()
    links = db.execute(
        select(Entity, EvidenceEntity)
        .join(EvidenceEntity, EvidenceEntity.entity_id == Entity.id)
        .where(EvidenceEntity.evidence_id == evidence.id)
    ).all()
    added = 0
    for entity, _link in links:
        if entity.type not in {EntityType.PERSON, EntityType.ORGANIZATION, EntityType.LOCATION}:
            continue
        if entity.normalized_value and entity.normalized_value in haystack:
            db.add(EventEntity(event_id=event.id, entity_id=entity.id, role=entity.type.value))
            added += 1
        if added >= 12:
            break
    if event.category == EventCategory.PHYSICAL:
        location = next(
            (entity for entity, _ in links if entity.type == EntityType.LOCATION and entity.normalized_value in haystack),
            None,
        )
        if location:
            event.meta = {**(event.meta or {}), "location": location.value}
