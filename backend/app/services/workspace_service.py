from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Evidence, User, Workspace

DEFAULT_WORKSPACE_NAME = "Default workspace"


def _unique_name(db: Session, user: User, base: str) -> str:
    # Names are unique in the database; suffix generated defaults when needed.
    name = base[:160]
    index = 2
    while db.scalar(select(Workspace).where(func.lower(Workspace.name) == name.lower())):
        suffix = f" ({index})"
        name = f"{base[: 160 - len(suffix)]}{suffix}"
        index += 1
    return name


def create_for_user(db: Session, user: User, name: str | None = None, *, is_default: bool = False) -> Workspace:
    workspace = Workspace(
        name=_unique_name(db, user, name or f"{user.display_name}'s workspace"),
        is_default=is_default,
        owner_id=user.id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_default(db: Session, user: User) -> Workspace:
    """Return the user's fallback workspace, creating one when needed."""
    workspace = db.scalar(
        select(Workspace).where(
            Workspace.owner_id == user.id,
            Workspace.is_default.is_(True),
        )
    )
    if workspace:
        return workspace
    workspace = db.scalar(
        select(Workspace).where(Workspace.owner_id == user.id).order_by(Workspace.created_at.asc()).limit(1)
    )
    if workspace:
        workspace.is_default = True
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace
    return create_for_user(db, user, name=f"{user.display_name}'s workspace", is_default=True)


def ensure_default_for_user(db: Session, user: User) -> Workspace:
    return get_default(db, user)


def resolve(db: Session, raw_id: str | None, user: User) -> Workspace:
    """Resolve X-Workspace-Id only when it belongs to the signed-in user."""
    if raw_id:
        try:
            workspace = db.get(Workspace, uuid.UUID(str(raw_id)))
        except (ValueError, TypeError):
            workspace = None
        if workspace and workspace.owner_id == user.id:
            return workspace
    return get_default(db, user)


def list_with_counts(db: Session, owner_id: uuid.UUID) -> list[tuple[Workspace, int]]:
    stmt = (
        select(Workspace, func.count(Evidence.id))
        .outerjoin(
            Evidence,
            (Evidence.workspace_id == Workspace.id) & (Evidence.deleted_at.is_(None)),
        )
        .where(Workspace.owner_id == owner_id)
        .group_by(Workspace.id)
        .order_by(Workspace.is_default.desc(), Workspace.created_at.asc())
    )
    return [(workspace, int(count)) for workspace, count in db.execute(stmt).all()]
