from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError, NotFoundError
from app.models import AuditLog, Evidence, Report, Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceList, WorkspaceOut, WorkspaceUpdate
from app.services import workspace_service
from app.services.audit_service import record_audit
from app.utils.http import actor_name, client_ip, user_agent

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _out(workspace: Workspace, evidence_count: int = 0) -> WorkspaceOut:
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        is_default=bool(workspace.is_default),
        evidence_count=evidence_count,
        created_at=workspace.created_at,
    )


def _evidence_count(db: Session, workspace_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count(Evidence.id)).where(
                Evidence.workspace_id == workspace_id,
                Evidence.deleted_at.is_(None),
            )
        )
        or 0
    )


@router.get("", response_model=WorkspaceList)
def list_workspaces(db: Session = Depends(get_db)):
    rows = workspace_service.list_with_counts(db)
    return WorkspaceList(items=[_out(workspace, count) for workspace, count in rows], total=len(rows))


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, request: Request, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise AppError(400, "invalid_workspace_name", "Workspace name cannot be blank.")
    exists = db.scalar(select(Workspace).where(func.lower(Workspace.name) == name.lower()))
    if exists:
        raise AppError(409, "workspace_exists", f'A workspace named "{name}" already exists.')

    workspace = Workspace(name=name)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    record_audit(
        db,
        actor=actor_name(request),
        action="Workspace created",
        target_type="workspace",
        target_id=str(workspace.id),
        details={"name": workspace.name},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=workspace.id,
    )
    return _out(workspace, 0)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def rename_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise NotFoundError("Workspace", workspace_id)
    name = payload.name.strip()
    if not name:
        raise AppError(400, "invalid_workspace_name", "Workspace name cannot be blank.")
    clash = db.scalar(
        select(Workspace).where(
            func.lower(Workspace.name) == name.lower(),
            Workspace.id != workspace.id,
        )
    )
    if clash:
        raise AppError(409, "workspace_exists", f'A workspace named "{name}" already exists.')

    previous = workspace.name
    workspace.name = name
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    record_audit(
        db,
        actor=actor_name(request),
        action="Workspace renamed",
        target_type="workspace",
        target_id=str(workspace.id),
        details={"from": previous, "to": name},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=workspace.id,
    )
    return _out(workspace, _evidence_count(db, workspace.id))


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise NotFoundError("Workspace", workspace_id)
    if workspace.is_default:
        raise AppError(400, "default_workspace", "The default workspace cannot be deleted.")

    fallback = workspace_service.get_default(db)
    if fallback.id == workspace.id:
        fallback = workspace_service.get_default(db)

    moved = db.execute(
        update(Evidence).where(Evidence.workspace_id == workspace.id).values(workspace_id=fallback.id)
    ).rowcount
    db.execute(update(Report).where(Report.workspace_id == workspace.id).values(workspace_id=fallback.id))
    db.execute(update(AuditLog).where(AuditLog.workspace_id == workspace.id).values(workspace_id=fallback.id))
    db.commit()

    name = workspace.name
    db.delete(workspace)
    db.commit()
    record_audit(
        db,
        actor=actor_name(request),
        action="Workspace deleted",
        target_type="workspace",
        target_id=str(workspace_id),
        details={"name": name, "movedEvidence": int(moved or 0), "movedTo": str(fallback.id)},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=fallback.id,
    )
    return {
        "id": str(workspace_id),
        "deleted": True,
        "movedEvidence": int(moved or 0),
        "movedTo": str(fallback.id),
    }
