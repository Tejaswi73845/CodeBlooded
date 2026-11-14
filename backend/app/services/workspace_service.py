from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Evidence, Workspace

DEFAULT_WORKSPACE_NAME = "Default workspace"


def get_default(db: Session) -> Workspace:
    workspace = db.scalar(select(Workspace).where(Workspace.is_default.is_(True)))
    if workspace:
        return workspace
    workspace = db.scalar(select(Workspace).order_by(Workspace.created_at.asc()).limit(1))
    if workspace:
        workspace.is_default = True
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace
    workspace = Workspace(name=DEFAULT_WORKSPACE_NAME, is_default=True)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def resolve(db: Session, raw_id: str | None) -> Workspace:
    """Resolve the X-Workspace-Id header, falling back to the default workspace."""
    if raw_id:
        try:
            workspace = db.get(Workspace, uuid.UUID(str(raw_id)))
        except (ValueError, TypeError):
            workspace = None
        if workspace:
            return workspace
    return get_default(db)


def list_with_counts(db: Session) -> list[tuple[Workspace, int]]:
    stmt = (
        select(Workspace, func.count(Evidence.id))
        .outerjoin(
            Evidence,
            (Evidence.workspace_id == Workspace.id) & (Evidence.deleted_at.is_(None)),
        )
        .group_by(Workspace.id)
        .order_by(Workspace.is_default.desc(), Workspace.created_at.asc())
    )
    return [(workspace, int(count)) for workspace, count in db.execute(stmt).all()]
