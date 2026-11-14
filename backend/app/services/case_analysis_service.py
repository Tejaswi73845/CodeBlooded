from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AIServiceError
from app.models import Evidence, ExtractedContent, TimelineEvent, Workspace
from app.schemas.report import CaseAnalysisOut, CaseTypeOut, UnrelatedEvidenceOut
from app.services.ai_service import ai_service
from app.utils.logging import get_logger
from app.utils.narrative import strip_header_syntax
from app.utils.text import truncate
from app.utils.time import utcnow

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a forensic case analyst. Using ONLY the supplied evidence, classify the case, "
    "write a detailed investigator summary, and flag evidence that is unrelated to the case. "
    "Allowed case-type labels: Fraud, Harassment, Assault, Sexual assault, Threats & extortion, "
    "Cybercrime, Theft, Defamation, Other. Never invent facts. "
    "Refer to dates in plain prose (this report stands alone), but never quote Message-IDs, "
    "IP addresses, angle-bracket email addresses or raw email header syntax. "
    "Return JSON: {\"caseTypes\":[{\"label\":\"Fraud\",\"confidence\":0.0-1.0}], "
    "\"summary\":\"6-10 factual sentences covering the key people, dates, amounts and events\", "
    "\"unrelated\":[{\"name\":\"exact file name\",\"reason\":\"why it is out of scope\"}]}."
)

RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Sexual assault", ("rape", "sexual assault", "molest", "sexual")),
    ("Assault", ("assault", "attack", "beat", "punch", "hit me", "injur")),
    ("Harassment", ("harass", "bully", "stalk", "abuse", "abusive")),
    ("Threats & extortion", ("threat", "blackmail", "extort", "or else", "pay or", "demand")),
    ("Fraud", ("fraud", "scam", "phishing", "payment", "transfer", "invest", "upi", "bank", "refund")),
    ("Cybercrime", ("hack", "malware", "otp", "account takeover", "device", "login")),
    ("Theft", ("theft", "stolen", "steal")),
    ("Defamation", ("defam", "reputation", "rumour", "rumor")),
]

_TEST_NAME = re.compile(r"(^|[_\-\s.])(test|sample|dummy|demo)([_\-\s.]|$)", re.IGNORECASE)

# Small in-process cache; keyed per workspace and invalidated when the evidence set changes.
_CACHE: dict[str, tuple[str, dict]] = {}


def analyze_case(db: Session, workspace: Workspace, *, refresh: bool = False) -> CaseAnalysisOut:
    rows = list(
        db.scalars(
            select(Evidence).where(
                Evidence.deleted_at.is_(None),
                Evidence.workspace_id == workspace.id,
            )
        ).all()
    )
    evidence_ids = [row.id for row in rows]
    events = (
        list(
            db.scalars(
                select(TimelineEvent)
                .where(TimelineEvent.evidence_id.in_(evidence_ids))
                .order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at)
                .limit(60)
            ).all()
        )
        if evidence_ids
        else []
    )

    digest = hashlib.sha256(
        "|".join(sorted(str(row.id) for row in rows) + sorted(str(event.id) for event in events)).encode()
    ).hexdigest()
    cached = _CACHE.get(str(workspace.id))
    if cached and cached[0] == digest and not refresh:
        return CaseAnalysisOut(**cached[1])

    if not rows:
        result = CaseAnalysisOut(
            case_types=[],
            summary="No preserved evidence is available for this workspace yet.",
            unrelated=[],
            mode="empty",
            generated_at=utcnow(),
        )
        _CACHE[str(workspace.id)] = (digest, result.model_dump())
        return result

    contents: dict[str, str] = {}
    for content in db.scalars(
        select(ExtractedContent)
        .where(ExtractedContent.evidence_id.in_(evidence_ids), ExtractedContent.text.is_not(None))
        .order_by(ExtractedContent.created_at)
    ).all():
        current = contents.get(str(content.evidence_id), "")
        if len(current) < 500 and content.text:
            contents[str(content.evidence_id)] = (current + "\n" + content.text)[:500].strip()

    corpus = " ".join(
        [
            *(row.original_filename for row in rows),
            *(row.note or "" for row in rows),
            *(event.title for event in events),
            *(event.description for event in events),
            *contents.values(),
        ]
    ).lower()

    labels = _heuristic_labels(corpus)
    fallback_summary = _fallback_summary(rows, events, labels)
    unrelated = _heuristic_unrelated(rows)
    mode = "heuristic"
    model: str | None = None
    limitations: list[str] = []

    if ai_service.configured:
        prompt = _build_prompt(rows, events, contents)
        try:
            payload = ai_service.generate_json(
                prompt,
                system=SYSTEM_PROMPT,
                temperature=0.1,
            )
            ai_types = _parse_types(payload)
            ai_summary = strip_header_syntax(str(payload.get("summary") or ""))
            ai_unrelated = _parse_unrelated(payload, rows)
            if ai_types:
                labels = ai_types
                mode = "ai"
                model = ai_service.model
            if ai_summary:
                fallback_summary = ai_summary
            if ai_unrelated:
                unrelated = ai_unrelated
        except AIServiceError as exc:
            logger.warning("Case analysis fell back to heuristics: %s", exc)
            limitations.append(f"AI case analysis unavailable ({truncate(exc.message, 160)}).")
    else:
        limitations.append("AI analysis is not configured; using keyword classification.")

    result = CaseAnalysisOut(
        case_types=[CaseTypeOut(**item) for item in labels],
        summary=fallback_summary,
        unrelated=[UnrelatedEvidenceOut(**item) for item in unrelated],
        mode=mode,
        model=model,
        generated_at=utcnow(),
        limitations=limitations,
    )
    _CACHE[str(workspace.id)] = (digest, result.model_dump())
    return result


def _heuristic_labels(corpus: str) -> list[dict]:
    labels: list[dict] = []
    for label, terms in RULES:
        hits = sum(1 for term in terms if term in corpus)
        if hits:
            labels.append({"label": label, "confidence": round(min(0.9, 0.5 + hits * 0.1), 2)})
    if not labels:
        return [{"label": "Other", "confidence": 0.3}]
    labels.sort(key=lambda item: item["confidence"], reverse=True)
    return labels[:3]


def _fallback_summary(rows: list[Evidence], events: list[TimelineEvent], labels: list[dict]) -> str:
    verified = sum(1 for row in rows if row.integrity_status.value == "verified")
    key_events = "; ".join(event.title for event in events[:5]) or "no dated events"
    label_text = ", ".join(item["label"] for item in labels)
    return (
        f"{len(rows)} evidence item(s) and {len(events)} timeline event(s) were analysed. "
        f"Indicators consistent with: {label_text}. "
        f"Key events: {key_events}. "
        f"Integrity: {verified} of {len(rows)} item(s) verified against their SHA-256 intake digest."
    )


def _heuristic_unrelated(rows: list[Evidence]) -> list[dict]:
    return [
        {
            "evidence_id": row.id,
            "name": row.original_filename,
            "reason": "Filename suggests a test or sample file rather than case material.",
        }
        for row in rows
        if _TEST_NAME.search(row.original_filename)
    ]


def _build_prompt(
    rows: list[Evidence],
    events: list[TimelineEvent],
    contents: dict[str, str],
) -> str:
    evidence_lines: list[str] = []
    for index, row in enumerate(rows[:12], start=1):
        capture = (row.meta or {}).get("capture") or {}
        detail = ", ".join(
            part
            for part in (
                capture.get("occurredAt"),
                capture.get("location"),
                ", ".join(capture.get("persons") or []),
            )
            if part
        )
        text = contents.get(str(row.id), "")
        evidence_lines.append(
            f"[E{index}] name: {row.original_filename} | type: {row.file_type.value} | "
            f"capture: {detail or 'none'} | note: {truncate(row.note or '', 160)}\n"
            f"text: {truncate(text, 400) or 'no extracted text'}"
        )
    event_lines = [
        f"[E{event.evidence_id}] {event.occurred_at_raw or (event.occurred_at.isoformat() if event.occurred_at else 'time unknown')} | "
        f"{event.title} | {event.category.value} | {event.severity} | {truncate(event.description, 180)}"
        for event in events[:30]
    ]
    return (
        "EVIDENCE:\n"
        + "\n\n".join(evidence_lines)
        + "\n\nTIMELINE EVENTS:\n"
        + ("\n".join(event_lines) or "none")
        + "\n\nClassify the case, write the detailed summary, and list any evidence that is unrelated "
        "to the case (for example test files, boilerplate or unrelated personal notes)."
    )


def _parse_types(payload: dict) -> list[dict]:
    raw = payload.get("caseTypes") or payload.get("case_types") or []
    parsed: list[dict] = []
    for item in raw[:5]:
        if isinstance(item, dict):
            label = str(item.get("label") or "").strip()
            try:
                confidence = float(item.get("confidence") or 0.5)
            except (TypeError, ValueError):
                confidence = 0.5
        elif isinstance(item, str):
            label = item.strip()
            confidence = 0.6
        else:
            continue
        if label:
            parsed.append(
                {"label": truncate(label, 40), "confidence": round(max(0.0, min(1.0, confidence)), 2)}
            )
    return parsed


def _parse_unrelated(payload: dict, rows: list[Evidence]) -> list[dict]:
    raw = payload.get("unrelated") or []
    by_name = {row.original_filename.lower(): row for row in rows}
    by_id = {str(row.id): row for row in rows}
    parsed: list[dict] = []
    for item in raw[:20]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        reason = str(item.get("reason") or "").strip()
        evidence_id = item.get("evidenceId") or item.get("evidence_id")
        row = by_name.get(name.lower()) or by_id.get(str(evidence_id))
        if not name and not row:
            continue
        parsed.append(
            {
                "evidence_id": row.id if row else None,
                "name": row.original_filename if row else name,
                "reason": truncate(reason or "Flagged as not related to the primary case type.", 400),
            }
        )
    return parsed
