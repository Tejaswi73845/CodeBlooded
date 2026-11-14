from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.timeline import TimelineEventOut, TimelinePage
from app.services import timeline_view_service
from app.utils.http import optional_uuid, parse_iso_date

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
    )


@router.get("/{event_id}", response_model=TimelineEventOut)
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    return timeline_view_service.get_timeline_event(db, event_id)
