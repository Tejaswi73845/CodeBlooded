from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_workspace
from app.errors import AppError
from app.models import Workspace
from app.schemas.timeline import (
    TimelineEventOut,
    TimelineEventUpdate,
    TimelinePage,
    TimelineSummaryRequest,
    TimelineSummaryResponse,
)
from app.services import timeline_summary_service, timeline_view_service
from app.services.audit_service import record_audit
from app.utils.http import actor_name, client_ip, optional_uuid, parse_iso_date, user_agent

router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.get("", response_model=TimelinePage)
def get_timeline(
    db: Session = Depends(get_db),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    person_id: str | None = Query(default=None, alias="personId"),
    person: str | None = Query(default=None),
    category: str | None = None,
    evidence_id: str | None = Query(default=None, alias="evidenceId"),
    uncertain: bool | None = None,
    q: str | None = Query(default=None, max_length=300),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    workspace: Workspace = Depends(current_workspace),
):
    return timeline_view_service.query_timeline(
        db,
        from_date=parse_iso_date(from_date or start),
        to_date=parse_iso_date(to_date or end),
        person_id=optional_uuid(person_id or person, "personId"),
        category=category,
        evidence_id=optional_uuid(evidence_id, "evidenceId"),
        uncertain=uncertain,
        q=q,
        limit=limit,
        offset=offset,
        workspace_id=workspace.id,
    )


@router.post("/summaries", response_model=TimelineSummaryResponse)
def summarize_timeline(
    payload: TimelineSummaryRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(current_workspace),
):
    items = timeline_summary_service.summarize_events(
        db,
        payload.event_ids,
        workspace.id,
        refresh=payload.refresh or bool(payload.context),
        context=payload.context,
    )
    return TimelineSummaryResponse(items=items)


@router.get("/{event_id}", response_model=TimelineEventOut)
def get_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(current_workspace),
):
    return timeline_view_service.get_timeline_event(db, event_id, workspace.id)


@router.patch("/{event_id}", response_model=TimelineEventOut)
def update_event(
    event_id: uuid.UUID,
    payload: TimelineEventUpdate,
    request: Request,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(current_workspace),
):
    try:
        updated = timeline_view_service.update_timeline_event(db, event_id, workspace.id, payload)
    except ValueError as exc:
        raise AppError(400, "invalid_datetime", str(exc)) from exc
    record_audit(
        db,
        actor=actor_name(request),
        action="Timeline event edited",
        target_type="timeline",
        target_id=str(event_id),
        details={
            "title": updated.title,
            "at": updated.at.isoformat() if updated.at else None,
            "location": updated.location,
        },
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=workspace.id,
    )
    return updated
