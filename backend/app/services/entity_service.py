from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entity, EntityRelationship, Evidence, EvidenceEntity, ExtractedContent
from app.models.enums import EntityType, EventCategory
from app.services.ai_service import ai_service
from app.utils.logging import get_logger
from app.utils.text import clean_text, excerpt_around, split_sentences, truncate
from app.utils.time import find_date_expressions, parse_event_datetime

logger = get_logger(__name__)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}(?!\w)")
PERSON_HEURISTIC = re.compile(r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){1,2}\b")
ORG_SUFFIX = re.compile(
    r"\b(?:[A-Z][\w&.'-]*\s*){1,4}(?:Ltd|Limited|LLP|Inc|Corp|Corporation|Pvt|Private|Bank|Enterprises|"
    r"Technologies|Solutions|Industries|Group)\b"
)
MONTHS = {
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
    "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}

_ner_model = None
_ner_checked = False
_ner_lock = threading.Lock()


@dataclass
class EntityCandidate:
    type: EntityType
    value: str
    normalized: str
    confidence: float
    excerpt: str
    source: str
    content_index: int = 0
    page_number: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventCandidate:
    title: str
    description: str
    date_raw: str | None
    occurred_at: datetime | None
    time_uncertain: bool
    category: EventCategory
    confidence: float
    excerpt: str
    severity: str = "info"
    page_number: int | None = None
    timestamp_start: float | None = None
    content_index: int = 0
    source: str = "gemini"


@dataclass
class ExtractionResult:
    entities: list[EntityCandidate] = field(default_factory=list)
    events: list[EventCandidate] = field(default_factory=list)
    provider: str = "regex"
    limitations: list[str] = field(default_factory=list)
    stored_entities: int = 0
    relationships: int = 0


ENTITY_SYSTEM_PROMPT = """You are a forensic evidence extraction engine.
Extract only information explicitly present in the supplied evidence text.
Never infer, complete, translate or invent names, numbers, dates or organizations.
Every entity and event MUST include a short verbatim excerpt copied from the text.
Preserve uncertainty: confidence must reflect how clearly the item is stated.
Dates must be copied exactly as written (date_raw) and may be partial.
Categories are Communication, Financial, Physical, Digital, Legal, Other.
Return JSON only, no markdown, with this shape:
{
  "entities": [
    {"type": "person|phone|email|organization|location|date|event|other",
     "value": "verbatim value", "confidence": 0.0-1.0, "excerpt": "verbatim source snippet"}
  ],
  "events": [
    {"title": "short factual label", "description": "one sentence from the source",
     "date_raw": "date/time as written or null", "category": "Communication|Financial|Physical|Digital|Legal|Other",
     "confidence": 0.0-1.0, "excerpt": "verbatim source snippet"}
  ]
}"""


def _load_ner():
    global _ner_model, _ner_checked
    with _ner_lock:
        if _ner_checked:
            return _ner_model
        _ner_checked = True
        try:
            import spacy  # type: ignore

            try:
                model = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model en_core_web_sm is not installed; using regex entity fallback.")
                return None
            if not model.has_pipe("ner"):
                return None
            _ner_model = model
        except ImportError:
            _ner_model = None
        return _ner_model


def normalize_entity(entity_type: EntityType, value: str) -> str:
    value = clean_text(value).strip(" \t\n,.;:()[]\"'")
    if entity_type == EntityType.PHONE:
        digits = re.sub(r"[^\d+]", "", value)
        if digits.startswith("00"):
            digits = "+" + digits[2:]
        return digits
    if entity_type in {EntityType.EMAIL}:
        return value.lower()
    if entity_type == EntityType.PERSON:
        return re.sub(r"\s+", " ", value).strip().lower()
    if entity_type == EntityType.ORGANIZATION:
        return re.sub(r"\s+", " ", value).strip().lower()
    if entity_type == EntityType.LOCATION:
        return re.sub(r"\s+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", value).strip().lower()


def _locate(contents: list[ExtractedContent], excerpt: str, value: str) -> tuple[int, ExtractedContent | None]:
    needle = (excerpt or value).lower()
    for index, content in enumerate(contents):
        haystack = clean_text(content.text).lower()
        if needle and needle in haystack:
            return index, content
        if value.lower() in haystack:
            return index, content
    return 0, contents[0] if contents else None


def _context(contents: list[ExtractedContent]) -> tuple[str, list[ExtractedContent]]:
    used: list[ExtractedContent] = []
    parts: list[str] = []
    total = 0
    for index, content in enumerate(contents):
        text = clean_text(content.text)
        if not text:
            continue
        locator = f"[BLOCK {index + 1} | {content.kind.value}"
        if content.page_number:
            locator += f" | page {content.page_number}"
        if content.timestamp_start is not None:
            locator += f" | {content.timestamp_start:.1f}s-{content.timestamp_end or content.timestamp_start:.1f}s"
        locator += "]"
        block = f"{locator}\n{text}"
        if total + len(block) > 24_000:
            remaining = max(0, 24_000 - total)
            block = block[:remaining]
        if len(block.strip()) > 5:
            parts.append(block)
            used.append(content)
            total += len(block)
        if total >= 24_000:
            break
    return "\n\n".join(parts), used


def extract_entities_for_evidence(db: Session, evidence: Evidence, contents: list[ExtractedContent]) -> ExtractionResult:
    contents = [content for content in contents if clean_text(content.text)]
    if not contents:
        return ExtractionResult(limitations=["No extractable text was available."])

    if ai_service.configured:
        try:
            result = _extract_with_gemini(contents)
            result.stored_entities, result.relationships = _persist(db, evidence, contents, result.entities)
            return result
        except Exception as exc:  # noqa: BLE001 - fall back to deterministic extraction
            logger.warning("Gemini entity extraction failed for %s: %s", evidence.id, exc)

    result = _extract_fallback(contents)
    if not ai_service.configured:
        result.limitations.append("GEMINI_API_KEY is not configured; deterministic extraction was used.")
    result.stored_entities, result.relationships = _persist(db, evidence, contents, result.entities)
    return result


def _extract_with_gemini(contents: list[ExtractedContent]) -> ExtractionResult:
    context, used = _context(contents)
    if not context:
        return ExtractionResult(provider="gemini", limitations=["No extractable text was available."])
    payload = ai_service.generate_json(
        "Extract entities and dated events from this evidence for a legal investigation.\n\n" + context,
        system=ENTITY_SYSTEM_PROMPT,
        temperature=0.0,
    )
    result = ExtractionResult(provider="gemini", limitations=[])
    if len(context) >= 24_000:
        result.limitations.append("Evidence text was truncated to the AI context budget.")

    by_type = {item.value: item for item in EntityType}
    for raw in payload.get("entities", [])[:300]:
        if not isinstance(raw, dict):
            continue
        raw_type = str(raw.get("type", "")).lower().strip()
        value = clean_text(str(raw.get("value", ""))).strip()
        excerpt = clean_text(str(raw.get("excerpt", ""))).strip()
        if not value or not excerpt:
            continue
        if raw_type not in by_type:
            raw_type = "other"
        entity_type = by_type[raw_type]
        source_text = clean_text(" ".join(content.text for content in used))
        if excerpt.lower() not in source_text.lower() or value.lower() not in source_text.lower():
            logger.info("Discarding unverifiable AI entity %r", value)
            continue
        try:
            confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        index, content = _locate(used, excerpt, value)
        result.entities.append(
            EntityCandidate(
                type=entity_type,
                value=value,
                normalized=normalize_entity(entity_type, value),
                confidence=confidence,
                excerpt=truncate(excerpt, 500),
                source="gemini",
                content_index=index,
                page_number=content.page_number if content else None,
                timestamp_start=content.timestamp_start if content else None,
                timestamp_end=content.timestamp_end if content else None,
            )
        )

    categories = {item.value.lower(): item for item in EventCategory}
    for raw in payload.get("events", [])[:120]:
        if not isinstance(raw, dict):
            continue
        title = clean_text(str(raw.get("title", "")))
        excerpt = clean_text(str(raw.get("excerpt", "")))
        if not title or not excerpt:
            continue
        source_text = clean_text(" ".join(content.text for content in used)).lower()
        if excerpt.lower() not in source_text:
            continue
        date_raw = clean_text(str(raw.get("date_raw") or "")) or None
        occurred_at, uncertain = parse_event_datetime(date_raw) if date_raw else (None, True)
        category = categories.get(str(raw.get("category", "")).lower(), EventCategory.OTHER)
        try:
            confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.6))))
        except (TypeError, ValueError):
            confidence = 0.6
        index, content = _locate(used, excerpt, excerpt[:40])
        result.events.append(
            EventCandidate(
                title=truncate(title, 140),
                description=truncate(clean_text(str(raw.get("description", ""))) or excerpt, 800),
                date_raw=date_raw,
                occurred_at=occurred_at,
                time_uncertain=uncertain,
                category=category,
                confidence=confidence,
                excerpt=truncate(excerpt, 500),
                page_number=content.page_number if content else None,
                timestamp_start=content.timestamp_start if content else None,
                content_index=index,
            )
        )
    return result


def _extract_fallback(contents: list[ExtractedContent]) -> ExtractionResult:
    result = ExtractionResult(provider="spacy+regex")
    ner = _load_ner()
    if ner is None:
        result.provider = "regex_fallback"
        result.limitations.append("spaCy NER is unavailable; person and organization recall is limited.")

    seen: dict[tuple[str, str], EntityCandidate] = {}

    def add(entity_type: EntityType, value: str, confidence: float, excerpt: str, index: int) -> None:
        value = clean_text(value)
        value = re.sub(r"\s+", " ", value).strip(" \t\n,.;:()[]\"'")
        if len(value) < 2 or len(value) > 200:
            return
        if entity_type == EntityType.PERSON:
            if any(char.isdigit() for char in value) or ORG_SUFFIX.search(value):
                return
            if value.lower() in MONTHS:
                return
        if entity_type == EntityType.DATE and not find_date_expressions(value):
            return
        if entity_type in {EntityType.ORGANIZATION, EntityType.LOCATION} and len(value) > 90:
            return
        normalized = normalize_entity(entity_type, value)
        if not normalized:
            return
        key = (entity_type.value, normalized)
        if key in seen:
            seen[key].confidence = max(seen[key].confidence, confidence)
            return
        seen[key] = EntityCandidate(
            type=entity_type,
            value=value,
            normalized=normalized,
            confidence=confidence,
            excerpt=truncate(excerpt, 500),
            source="spacy" if ner is not None else "regex_fallback",
            content_index=index,
        )

    for index, content in enumerate(contents):
        text = clean_text(content.text)
        sentences = split_sentences(text)

        for email in EMAIL_RE.findall(text):
            add(EntityType.EMAIL, email, 0.95, excerpt_around(text, email), index)
        for phone in PHONE_RE.findall(text):
            digits = re.sub(r"\D", "", phone)
            if 8 <= len(digits) <= 15:
                add(EntityType.PHONE, phone.strip(), 0.8, excerpt_around(text, phone), index)
        for org in ORG_SUFFIX.findall(text):
            if len(org) > 3:
                add(EntityType.ORGANIZATION, org.strip(), 0.7, excerpt_around(text, org), index)
        for raw_date in find_date_expressions(text):
            parsed, uncertain = parse_event_datetime(raw_date)
            add(
                EntityType.DATE,
                raw_date,
                0.65 if parsed and not uncertain else 0.5,
                excerpt_around(text, raw_date),
                index,
            )

        if ner is not None:
            doc = ner(text[:20000])
            mapping = {
                "PERSON": EntityType.PERSON,
                "ORG": EntityType.ORGANIZATION,
                "GPE": EntityType.LOCATION,
                "LOC": EntityType.LOCATION,
                "FAC": EntityType.LOCATION,
                "DATE": EntityType.DATE,
            }
            for ent in doc.ents:
                if ent.label_ not in mapping:
                    continue
                value = clean_text(ent.text).strip()
                if value.lower() in MONTHS or value.lower() in {"today", "yesterday", "tomorrow"}:
                    continue
                add(mapping[ent.label_], value, 0.72, excerpt_around(text, value), index)
        else:
            for match in PERSON_HEURISTIC.findall(text):
                if match.lower() in MONTHS or ORG_SUFFIX.search(match):
                    continue
                first = match.split()[0]
                if first in {"The", "This", "That", "From", "Dear", "Subject", "Re", "Page", "Case"}:
                    continue
                add(EntityType.PERSON, match, 0.4, excerpt_around(text, match), index)

        # A conservative event candidate for every sentence with an explicit date.
        for sentence in sentences:
            dates = find_date_expressions(sentence)
            if not dates:
                continue
            raw_date = dates[0]
            occurred_at, uncertain = parse_event_datetime(raw_date)
            result.events.append(
                EventCandidate(
                    title=truncate(sentence, 110),
                    description=truncate(sentence, 700),
                    date_raw=raw_date,
                    occurred_at=occurred_at,
                    time_uncertain=uncertain,
                    category=_categorize(sentence),
                    confidence=0.55 if uncertain else 0.65,
                    excerpt=truncate(sentence, 500),
                    page_number=content.page_number,
                    timestamp_start=content.timestamp_start,
                    content_index=index,
                    source="regex",
                )
            )

    result.entities = list(seen.values())
    return result


def _categorize(text: str) -> EventCategory:
    lowered = text.lower()
    if any(word in lowered for word in ("transfer", "payment", "₹", "rs.", "inr", "bank", "invoice", "amount")):
        return EventCategory.FINANCIAL
    if any(word in lowered for word in ("message", "whatsapp", "email", "call", "chat", "dm", "threat")):
        return EventCategory.COMMUNICATION
    if any(word in lowered for word in ("cctv", "camera", "entered", "exited", "parking", "meeting", "visited")):
        return EventCategory.PHYSICAL
    if any(word in lowered for word in ("filed", "court", "statement", "interview", "counsel", "legal", "report")):
        return EventCategory.LEGAL
    if any(word in lowered for word in ("login", "device", "account", "hash", "metadata", "export", "server")):
        return EventCategory.DIGITAL
    return EventCategory.OTHER


def _persist(
    db: Session, evidence: Evidence, contents: list[ExtractedContent], candidates: list[EntityCandidate]
) -> tuple[int, int]:
    if not candidates:
        return 0, 0
    stored: dict[tuple[str, str], Entity] = {}
    for candidate in candidates[:250]:
        entity = db.scalar(
            select(Entity).where(
                Entity.type == candidate.type,
                Entity.normalized_value == candidate.normalized,
            )
        )
        if entity:
            entity.mention_count += 1
            entity.confidence = max(entity.confidence, candidate.confidence)
            entity.last_seen_at = max(entity.last_seen_at, evidence.uploaded_at)
            if entity.source != "gemini" and candidate.source == "gemini":
                entity.source = "gemini"
            db.add(entity)
        else:
            entity = Entity(
                type=candidate.type,
                value=candidate.value[:500],
                normalized_value=candidate.normalized[:500],
                confidence=candidate.confidence,
                source=candidate.source,
                mention_count=1,
                meta={"firstEvidenceId": str(evidence.id)},
            )
            db.add(entity)
            db.flush()
        stored[(candidate.type.value, candidate.normalized)] = entity

        link = db.get(EvidenceEntity, {"evidence_id": evidence.id, "entity_id": entity.id})
        if link:
            link.occurrence_count += 1
            if len(candidate.excerpt or "") > len(link.excerpt or ""):
                link.excerpt = candidate.excerpt
        else:
            link = EvidenceEntity(
                evidence_id=evidence.id,
                entity_id=entity.id,
                occurrence_count=1,
                excerpt=candidate.excerpt,
                meta={
                    "pageNumber": candidate.page_number,
                    "timestampStart": candidate.timestamp_start,
                    "timestampEnd": candidate.timestamp_end,
                },
            )
            db.add(link)

    db.commit()

    # Co-occurrence relationships, constrained to entities in the same text block.
    by_block: dict[int, list[tuple[EntityCandidate, Entity]]] = {}
    for candidate in candidates[:250]:
        entity = stored.get((candidate.type.value, candidate.normalized))
        if entity:
            by_block.setdefault(candidate.content_index, []).append((candidate, entity))

    relationships = 0
    existing_pairs = {
        (str(r.from_entity_id), str(r.to_entity_id))
        for r in db.scalars(select(EntityRelationship).where(EntityRelationship.evidence_id == evidence.id)).all()
    }
    for block_index, items in by_block.items():
        unique: dict[str, tuple[EntityCandidate, Entity]] = {str(entity.id): (candidate, entity) for candidate, entity in items}
        values = list(unique.values())
        for left_index in range(len(values)):
            for right_index in range(left_index + 1, min(len(values), left_index + 8)):
                left_candidate, left = values[left_index]
                right_candidate, right = values[right_index]
                pair = (str(left.id), str(right.id))
                if pair in existing_pairs or pair[::-1] in existing_pairs:
                    continue
                if {left.type, right.type} <= {EntityType.DATE, EntityType.PHONE}:
                    continue
                rel_type = _relationship_type(left.type, right.type)
                context = truncate(left_candidate.excerpt if len(left_candidate.excerpt) < len(right_candidate.excerpt) else right_candidate.excerpt, 400)
                db.add(
                    EntityRelationship(
                        from_entity_id=left.id,
                        to_entity_id=right.id,
                        evidence_id=evidence.id,
                        relationship_type=rel_type,
                        context=context,
                        confidence=min(left_candidate.confidence, right_candidate.confidence),
                    )
                )
                existing_pairs.add(pair)
                relationships += 1
                if relationships >= 120:
                    break
            if relationships >= 120:
                break
    db.commit()
    logger.info("Stored %d entities and %d relationships for evidence %s", len(stored), relationships, evidence.id)
    return len(stored), relationships


def _relationship_type(left: EntityType, right: EntityType) -> str:
    types = {left, right}
    if EntityType.PERSON in types and EntityType.PHONE in types:
        return "person_phone"
    if EntityType.PERSON in types and EntityType.EMAIL in types:
        return "person_email"
    if EntityType.PERSON in types and EntityType.ORGANIZATION in types:
        return "person_organization"
    if EntityType.PERSON in types and EntityType.LOCATION in types:
        return "person_location"
    return "mentioned_together"
