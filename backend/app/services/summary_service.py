from __future__ import annotations

import hashlib
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AIServiceError
from app.models import Evidence
from app.schemas.evidence import EvidenceAiSummary
from app.services.ai_service import ai_service
from app.utils.logging import get_logger
from app.utils.text import truncate
from app.utils.time import utcnow

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You summarise digital evidence for a forensic investigator. "
    "Use only the supplied file text. Never invent names, dates, amounts or events. "
    "Be factual and concise: 3–4 sentences, mentioning the key people, times, places and amounts "
    "that actually appear. If the text is unreadable or empty, say so."
)


def summarize(db: Session, evidence: Evidence, *, refresh: bool = False) -> EvidenceAiSummary:
    meta = evidence.meta or {}
    contents = sorted(
        evidence.extracted_content,
        key=lambda item: (item.page_number or 0, item.created_at),
    )
    text = "\n\n".join(content.text for content in contents if content.text).strip()
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "empty"

    cached = meta.get("aiSummary")
    if (
        not refresh
        and isinstance(cached, dict)
        and cached.get("summary")
        and cached.get("contentHash") == content_hash
    ):
        return _from_cache(evidence, cached)

    capture = meta.get("capture") or {}
    limitations: list[str] = []
    model: str | None = None
    mode = "metadata"

    if not text:
        summary = _metadata_summary(evidence, capture)
    elif ai_service.configured:
        try:
            prompt = (
                f"FILE: {evidence.original_filename}\n"
                f"TYPE: {evidence.file_type.value}\n\n"
                f"TEXT:\n{truncate(text, settings.max_text_chars_for_ai)}"
            )
            result = ai_service.generate(prompt, system=SYSTEM_PROMPT, temperature=0.1)
            summary = result.text.strip()
            mode = "ai"
            model = result.model
        except AIServiceError as exc:
            logger.warning("Evidence summary fell back to extraction for %s: %s", evidence.id, exc)
            summary = _extractive_summary(text)
            mode = "extractive"
            limitations.append(f"AI summary unavailable ({truncate(exc.message, 160)}); showing extracted text.")
    else:
        summary = _extractive_summary(text)
        mode = "extractive"
        limitations.append("AI synthesis is not configured; showing extracted text.")

    payload = {
        "summary": summary,
        "mode": mode,
        "model": model,
        "limitations": limitations,
        "contentHash": content_hash,
        "generatedAt": utcnow().isoformat(),
    }
    evidence.meta = {**meta, "aiSummary": payload}
    db.add(evidence)
    db.commit()

    return EvidenceAiSummary(
        evidence_id=evidence.id,
        evidence_name=evidence.original_filename,
        summary=summary,
        mode=mode,
        model=model,
        cached=False,
        generated_at=utcnow(),
        limitations=limitations,
    )


def _from_cache(evidence: Evidence, cached: dict) -> EvidenceAiSummary:
    return EvidenceAiSummary(
        evidence_id=evidence.id,
        evidence_name=evidence.original_filename,
        summary=str(cached.get("summary") or ""),
        mode=str(cached.get("mode") or "ai"),
        model=cached.get("model"),
        cached=True,
        generated_at=str(cached.get("generatedAt") or utcnow().isoformat()),
        limitations=[str(item) for item in cached.get("limitations") or []],
    )


def _extractive_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return truncate(cleaned, 700)


def _metadata_summary(evidence: Evidence, capture: dict) -> str:
    parts = [
        f"No readable text could be extracted from “{evidence.original_filename}” "
        f"({evidence.file_type.value} file, {_size(evidence.size_bytes)})."
    ]
    occurred = capture.get("occurredAt")
    if occurred:
        parts.append(f"Recorded at {str(occurred).replace('T', ' ')[:16]}.")
    location = capture.get("location")
    if location:
        parts.append(f"Location: {location}.")
    persons = capture.get("persons") or []
    if persons:
        parts.append(f"People: {', '.join(str(person) for person in persons[:6])}.")
    if capture.get("note"):
        parts.append(f"Note: {capture['note']}.")
    return " ".join(parts)


def _size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"
