from __future__ import annotations

import io
import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import NotFoundError, ProcessingError
from app.models import Entity, EntityRelationship, Evidence, EvidenceEntity, Report, TimelineEvent
from app.models.enums import EntityType, EvidenceStatus, IntegrityStatus, ReportStatus
from app.schemas.report import ReportGenerateRequest, ReportOut, ReportSummary
from app.services.ai_service import ai_service
from app.utils.logging import get_logger
from app.utils.text import truncate
from app.utils.time import utcnow

logger = get_logger(__name__)


def generate_report(db: Session, request: ReportGenerateRequest, actor: str) -> Report:
    stmt = select(Evidence).where(Evidence.deleted_at.is_(None))
    if request.evidence_ids:
        stmt = stmt.where(Evidence.id.in_(request.evidence_ids))
    evidence_rows = list(db.scalars(stmt.order_by(Evidence.uploaded_at.asc())).all())
    if not evidence_rows:
        raise ProcessingError("No preserved evidence is available to build a report.")

    evidence_ids = [row.id for row in evidence_rows]
    events = list(
        db.scalars(
            select(TimelineEvent)
            .where(TimelineEvent.evidence_id.in_(evidence_ids))
            .order_by(TimelineEvent.occurred_at.is_(None), TimelineEvent.occurred_at, TimelineEvent.created_at)
        ).all()
    )
    person_rows = db.execute(
        select(Entity, func.count(EvidenceEntity.evidence_id))
        .join(EvidenceEntity, EvidenceEntity.entity_id == Entity.id)
        .where(Entity.type == EntityType.PERSON, EvidenceEntity.evidence_id.in_(evidence_ids))
        .group_by(Entity.id)
        .order_by(func.sum(EvidenceEntity.occurrence_count).desc())
    ).all()
    relationships = db.scalars(
        select(EntityRelationship).where(EntityRelationship.evidence_id.in_(evidence_ids)).limit(200)
    ).all()

    integrity_counts = {
        "total": len(evidence_rows),
        "verified": sum(1 for row in evidence_rows if row.integrity_status == IntegrityStatus.VERIFIED),
        "pending": sum(1 for row in evidence_rows if row.integrity_status == IntegrityStatus.PENDING),
        "mismatch": sum(1 for row in evidence_rows if row.integrity_status == IntegrityStatus.MISMATCH),
    }

    chronology = [
        {
            "id": str(event.id),
            "at": event.occurred_at.isoformat() if event.occurred_at else None,
            "atRaw": event.occurred_at_raw,
            "timeUncertain": event.time_uncertain,
            "title": event.title,
            "description": event.description,
            "category": event.category.value,
            "severity": event.severity,
            "confidence": event.confidence,
            "evidenceId": str(event.evidence_id),
            "evidenceName": next(
                (row.original_filename for row in evidence_rows if row.id == event.evidence_id), "Unknown"
            ),
            "pageNumber": event.page_number,
            "sourceTimestamp": event.source_timestamp,
            "people": [
                link.entity.value
                for link in event.entity_links
                if link.entity and link.entity.type == EntityType.PERSON
            ],
        }
        for event in events[:300]
    ]

    people = [
        {
            "id": str(entity.id),
            "name": entity.value,
            "mentions": entity.mention_count,
            "evidenceCount": evidence_count,
            "confidence": entity.confidence,
            "phone": _related_value(db, entity.id, EntityType.PHONE),
            "email": _related_value(db, entity.id, EntityType.EMAIL),
        }
        for entity, evidence_count in person_rows
    ]

    evidence_register = [
        {
            "id": str(row.id),
            "reference": row.reference,
            "name": row.original_filename,
            "type": row.file_type.value,
            "size": row.size_bytes,
            "sha256": row.sha256,
            "integrity": row.integrity_status.value,
            "status": row.status.value,
            "uploadedAt": row.uploaded_at.isoformat(),
            "pages": (row.meta or {}).get("pages"),
            "duration": (row.meta or {}).get("duration"),
            "duplicateOf": str(row.duplicate_of_id) if row.duplicate_of_id else None,
        }
        for row in evidence_rows
    ]

    review_items = _review_items(evidence_rows, events)
    summary, generated_by, model, limitations = _summary(
        db, evidence_rows, events, people, integrity_counts, request.include_ai_summary
    )
    dated = [event.occurred_at for event in events if event.occurred_at]
    content = {
        "generatedAt": utcnow().isoformat(),
        "caseId": "TraceVault matter",
        "dateRange": {
            "earliest": min(dated).isoformat() if dated else None,
            "latest": max(dated).isoformat() if dated else None,
        },
        "summary": summary,
        "findings": [
            {
                "title": "Preserved evidence register",
                "detail": f"{len(evidence_rows)} items preserved; {integrity_counts['verified']} verified, "
                f"{integrity_counts['mismatch']} mismatch, {integrity_counts['pending']} pending.",
                "severity": "warning" if integrity_counts["mismatch"] else "info",
            },
            {
                "title": "Chronology",
                "detail": f"{len(events)} events reconstructed from source text; "
                f"{sum(1 for event in events if event.time_uncertain)} carry partial or uncertain timestamps.",
                "severity": "info",
            },
            {
                "title": "People identified",
                "detail": f"{len(people)} person entities resolved with {len(relationships)} documented relationships.",
                "severity": "info",
            },
        ],
        "chronology": chronology,
        "people": people,
        "evidence": evidence_register,
        "integrity": {
            **integrity_counts,
            "algorithm": "SHA-256",
            "generatedAt": utcnow().isoformat(),
        },
        "reviewItems": review_items,
        "limitations": limitations,
    }
    markdown = _markdown(request.title, content, generated_by, model)
    report = Report(
        title=request.title or f"Evidence Intelligence Report — {utcnow().date().isoformat()}",
        report_type=request.report_type,
        status=ReportStatus.FINAL if not review_items else ReportStatus.REVIEW,
        content=content,
        markdown=markdown,
        evidence_ids=[str(row.id) for row in evidence_rows],
        author=actor,
        generated_by=generated_by,
        model=model,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, limit: int = 20, offset: int = 0) -> tuple[list[ReportSummary], int]:
    total = int(db.scalar(select(func.count(Report.id))) or 0)
    rows = db.scalars(select(Report).order_by(Report.created_at.desc()).limit(limit).offset(offset)).all()
    return [serialize_report_summary(row) for row in rows], total


def get_report(db: Session, report_id: uuid.UUID) -> Report:
    report = db.get(Report, report_id)
    if not report:
        raise NotFoundError("Report", report_id)
    return report


def serialize_report(report: Report) -> ReportOut:
    content = report.content or {}
    return ReportOut(
        id=report.id,
        title=report.title,
        type=report.report_type,
        status=report.status.value,
        author=report.author,
        created_at=report.created_at,
        pages=max(1, math.ceil(len(report.markdown or "") / 3200)),
        evidence_count=len(report.evidence_ids or []),
        generated_by=report.generated_by,
        model=report.model,
        content=content,
        markdown=report.markdown,
    )


def serialize_report_summary(report: Report) -> ReportSummary:
    return ReportSummary(
        id=report.id,
        title=report.title,
        type=report.report_type,
        status=report.status.value,
        author=report.author,
        created_at=report.created_at,
        pages=max(1, math.ceil(len(report.markdown or "") / 3200)),
        evidence_count=len(report.evidence_ids or []),
        generated_by=report.generated_by,
    )


def _related_value(db: Session, entity_id: uuid.UUID, target_type: EntityType) -> str | None:
    row = db.execute(
        select(Entity.value)
        .join(EntityRelationship, EntityRelationship.to_entity_id == Entity.id)
        .where(EntityRelationship.from_entity_id == entity_id, Entity.type == target_type)
        .limit(1)
    ).first()
    if row:
        return row[0]
    row = db.execute(
        select(Entity.value)
        .join(EntityRelationship, EntityRelationship.from_entity_id == Entity.id)
        .where(EntityRelationship.to_entity_id == entity_id, Entity.type == target_type)
        .limit(1)
    ).first()
    return row[0] if row else None


def _review_items(evidence_rows: list[Evidence], events: list[TimelineEvent]) -> list[dict]:
    items: list[dict] = []
    for row in evidence_rows:
        if row.integrity_status == IntegrityStatus.MISMATCH:
            items.append(
                {
                    "severity": "critical",
                    "title": "Integrity mismatch",
                    "detail": f"{row.original_filename} does not match its intake SHA-256 digest.",
                    "evidenceId": str(row.id),
                }
            )
        if row.status == EvidenceStatus.FAILED:
            items.append(
                {
                    "severity": "warning",
                    "title": "Processing failed",
                    "detail": f"{row.original_filename}: {row.error_message or 'unknown processing error'}",
                    "evidenceId": str(row.id),
                }
            )
        if row.duplicate_of_id:
            items.append(
                {
                    "severity": "warning",
                    "title": "Duplicate preserved",
                    "detail": f"{row.original_filename} is an exact duplicate; both copies were preserved.",
                    "evidenceId": str(row.id),
                }
            )
    uncertain = [event for event in events if event.time_uncertain]
    if uncertain:
        items.append(
            {
                "severity": "warning",
                "title": "Uncertain timestamps",
                "detail": f"{len(uncertain)} events have missing or partial timestamps; re-verify against sources.",
                "evidenceId": None,
            }
        )
    return items[:12]


def _summary(
    db: Session,
    evidence_rows: list[Evidence],
    events: list[TimelineEvent],
    people: list[dict],
    integrity: dict,
    include_ai: bool,
) -> tuple[list[str], str, str | None, list[str]]:
    deterministic = [
        f"{len(evidence_rows)} digital evidence items were preserved across "
        f"{', '.join(sorted({row.file_type.value for row in evidence_rows}))} sources. "
        f"{integrity['verified']} of {integrity['total']} items passed SHA-256 integrity verification.",
        f"{len(events)} events were reconstructed from extracted text. "
        f"{sum(1 for event in events if event.time_uncertain)} carry partial or uncertain timestamps.",
        f"{len(people)} person entities were resolved from the preserved records. "
        "Entity links indicate co-occurrence in source text, not proof of involvement.",
    ]
    limitations: list[str] = []
    if not include_ai or not ai_service.configured:
        if include_ai and not ai_service.configured:
            limitations.append("GEMINI_API_KEY is not configured; summary is deterministic.")
        return deterministic, "deterministic", None, limitations

    digest_parts = []
    for row in evidence_rows[:8]:
        text = "\n".join(content.text for content in row.extracted_content if content.text)
        digest_parts.append(f"[{row.reference}] {row.original_filename} ({row.file_type.value})\n{truncate(text, 1200)}")
    event_lines = "\n".join(
        f"- {event.occurred_at_raw or (event.occurred_at.isoformat() if event.occurred_at else 'time unknown')}: {event.title}"
        for event in events[:20]
    )
    prompt = (
        "Write a factual incident summary from the preserved evidence below. Use only the supplied material. "
        "Return 2-3 short paragraphs. Do not invent names, amounts or dates; state uncertainty where present. "
        "Do not make legal conclusions.\n\nEVIDENCE:\n"
        + "\n\n".join(digest_parts)
        + "\n\nTIMELINE:\n"
        + event_lines
    )
    try:
        result = ai_service.generate(
            prompt,
            system=(
                "You are a forensic report writer. Ground every statement in the supplied evidence. "
                "Never fabricate. Preserve uncertainty and distinguish facts from inference."
            ),
            temperature=0.2,
        )
        paragraphs = [paragraph.strip() for paragraph in result.text.split("\n\n") if paragraph.strip()]
        if paragraphs:
            return paragraphs[:4], "gemini", result.model, limitations
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini report summary failed: %s", exc)
        limitations.append(f"AI summary unavailable: {truncate(str(exc), 160)}")
    return deterministic, "deterministic", None, limitations


def _markdown(title: str | None, content: dict, generated_by: str, model: str | None) -> str:
    lines: list[str] = []
    lines.append(f"# {title or 'Evidence Intelligence Report'}")
    lines.append("")
    lines.append(f"Generated {content['generatedAt']} · {generated_by}" + (f" · {model}" if model else ""))
    lines.append("")
    lines.append("## 01 · Summary")
    for paragraph in content["summary"]:
        lines.append(paragraph)
        lines.append("")
    lines.append("## 02 · Findings")
    for finding in content["findings"]:
        lines.append(f"- **{finding['title']}** — {finding['detail']}")
    if content["reviewItems"]:
        lines.append("")
        lines.append("### Items requiring review")
        for item in content["reviewItems"]:
            lines.append(f"- {item['title']}: {item['detail']}")
    lines.append("")
    lines.append("## 03 · Chronology")
    for event in content["chronology"]:
        when = event["atRaw"] or event["at"] or "time unknown"
        uncertain = " *(time uncertain)*" if event["timeUncertain"] else ""
        lines.append(f"- **{when}**{uncertain} — {event['title']} ({event['category']}) — {event['evidenceName']}")
    lines.append("")
    lines.append("## 04 · People")
    for person in content["people"]:
        lines.append(f"- **{person['name']}** — {person['mentions']} mentions across {person['evidenceCount']} items")
    lines.append("")
    lines.append("## 05 · Evidence register")
    for item in content["evidence"]:
        lines.append(
            f"- {item['reference']} · {item['name']} · {item['integrity']} · SHA-256 `{item['sha256']}`"
        )
    lines.append("")
    lines.append("## 06 · Integrity")
    lines.append(
        f"{content['integrity']['verified']} verified · {content['integrity']['pending']} pending · "
        f"{content['integrity']['mismatch']} mismatch · {content['integrity']['algorithm']}"
    )
    return "\n".join(lines)


def render_report_pdf(report: Report) -> io.BytesIO:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ProcessingError("PDF export requires reportlab (see requirements.txt).") from exc

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=report.title,
        author=report.author,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TVTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, spaceAfter=4
    )
    heading = ParagraphStyle(
        "TVHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, spaceBefore=10,
        spaceAfter=5, textColor=colors.HexColor("#1d1d1f"),
    )
    body = ParagraphStyle("TVBody", parent=styles["BodyText"], fontSize=8.8, leading=13, textColor=colors.HexColor("#3a3a3c"))
    small = ParagraphStyle("TVSmall", parent=body, fontSize=7.4, leading=10, textColor=colors.HexColor("#6e6e73"))

    story = [
        Paragraph("TRACEVAULT · EVIDENCE INTELLIGENCE", small),
        Paragraph(report.title, title_style),
        Paragraph(
            f"Matter reference: {', '.join(report.evidence_ids[:3]) or '—'} · Generated "
            f"{report.created_at.strftime('%d %b %Y, %H:%M')} · {report.author}",
            small,
        ),
        Spacer(1, 8),
    ]

    content = report.content or {}
    story.append(Paragraph("01 · Incident summary", heading))
    for paragraph in content.get("summary", []):
        story.append(Paragraph(paragraph, body))
        story.append(Spacer(1, 4))

    story.append(Paragraph("02 · Findings and review items", heading))
    for finding in content.get("findings", []):
        story.append(Paragraph(f"<b>{finding['title']}</b> — {finding['detail']}", body))
    for item in content.get("reviewItems", []):
        story.append(Paragraph(f"<b>{item['title']}</b> — {item['detail']}", body))
    story.append(PageBreak())

    story.append(Paragraph("03 · Chronology", heading))
    chronology = content.get("chronology", [])
    if chronology:
        rows = [["Timestamp", "Event", "Category", "Source"]]
        for event in chronology[:120]:
            when = event.get("atRaw") or event.get("at") or "time unknown"
            if event.get("timeUncertain"):
                when += " (uncertain)"
            rows.append([when, event.get("title", ""), event.get("category", ""), event.get("evidenceName", "")])
        table = Table(rows, colWidths=[36 * mm, 72 * mm, 22 * mm, 42 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 7.2),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6e6e73")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#d2d2d7")),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#e5e5ea")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.extend([table, Spacer(1, 8)])

    story.append(Paragraph("04 · People involved", heading))
    for person in content.get("people", []):
        story.append(
            Paragraph(
                f"<b>{person['name']}</b> — {person['mentions']} mentions across {person['evidenceCount']} items",
                body,
            )
        )

    story.append(Paragraph("05 · Evidence register", heading))
    register = content.get("evidence", [])
    if register:
        rows = [["Reference", "File", "Integrity", "SHA-256"]]
        for item in register:
            rows.append(
                [
                    item.get("reference", ""),
                    item.get("name", ""),
                    item.get("integrity", ""),
                    (item.get("sha256", "")[:16] + "…"),
                ]
            )
        table = Table(rows, colWidths=[28 * mm, 76 * mm, 20 * mm, 48 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 7.2),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6e6e73")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#d2d2d7")),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#e5e5ea")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)

    integrity = content.get("integrity", {})
    story.append(Paragraph("06 · Integrity statement", heading))
    story.append(
        Paragraph(
            f"{integrity.get('verified', 0)} of {integrity.get('total', 0)} items verified · "
            f"{integrity.get('mismatch', 0)} mismatch · algorithm {integrity.get('algorithm', 'SHA-256')}. "
            "Original files are immutable and every access is recorded in the chained audit ledger.",
            small,
        )
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#86868b"))
        canvas.drawString(18 * mm, 10 * mm, "TraceVault · Confidential · Evidence-backed report")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer
