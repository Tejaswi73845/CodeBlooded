from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_workspace
from app.models import Workspace
from app.schemas.entity import EntityDetail, EntityGraph, EntityPage
from app.services import entity_view_service
from app.utils.http import optional_uuid

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("", response_model=EntityPage)
def list_entities(
    db: Session = Depends(get_db),
    entity_type: str | None = Query(default=None, alias="type"),
    q: str | None = Query(default=None, max_length=300),
    evidence_id: str | None = Query(default=None, alias="evidenceId"),
    limit: int = Query(default=50, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    workspace: Workspace = Depends(current_workspace),
):
    items, total = entity_view_service.list_entities(
        db,
        type_filter=entity_type,
        q=q,
        evidence_id=optional_uuid(evidence_id, "evidenceId"),
        limit=limit,
        offset=offset,
        workspace_id=workspace.id,
    )
    return EntityPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/graph", response_model=EntityGraph)
def graph(
    db: Session = Depends(get_db),
    types: str | None = None,
    q: str | None = Query(default=None, max_length=300),
    include_events: bool = Query(default=True, alias="includeEvents"),
    limit: int = Query(default=150, ge=1, le=400),
    workspace: Workspace = Depends(current_workspace),
):
    return entity_view_service.build_graph(
        db,
        types=types,
        q=q,
        include_events=include_events,
        limit=limit,
        workspace_id=workspace.id,
    )


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(current_workspace),
):
    return entity_view_service.get_entity_detail(db, entity_id, workspace.id)
