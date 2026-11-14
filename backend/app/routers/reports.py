from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report import ReportGenerateRequest, ReportOut, ReportPage
from app.services import report_service
from app.services.audit_service import record_audit
from app.utils.http import actor_name, client_ip, user_agent
from app.utils.text import slugify

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate_report(payload: ReportGenerateRequest, request: Request, db: Session = Depends(get_db)):
    actor = payload.actor or actor_name(request)
    report = report_service.generate_report(db, payload, actor)
    record_audit(
        db,
        actor=actor,
        action="Report generated",
        target_type="report",
        target_id=str(report.id),
        details={
            "title": report.title,
            "type": report.report_type,
            "evidenceCount": len(report.evidence_ids or []),
            "generatedBy": report.generated_by,
        },
        ip_address=client_ip(request),
        user_agent=user_agent(request),
    )
    return report_service.serialize_report(report)


@router.get("", response_model=ReportPage)
def list_reports(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items, total = report_service.list_reports(db, limit=limit, offset=offset)
    return ReportPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    return report_service.serialize_report(report_service.get_report(db, report_id))


@router.get("/{report_id}/pdf")
def download_report_pdf(report_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    report = report_service.get_report(db, report_id)
    buffer = report_service.render_report_pdf(report)
    record_audit(
        db,
        actor=actor_name(request),
        action="Report exported",
        target_type="report",
        target_id=str(report.id),
        details={"title": report.title, "format": "pdf"},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
    )
    filename = f"{slugify(report.title)}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
