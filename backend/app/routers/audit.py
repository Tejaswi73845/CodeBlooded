from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_workspace
from app.models import AuditLog, Workspace
from app.models.enums import AuditResult
from app.schemas.audit import AuditEntryOut, AuditPage, AuditVerify
from app.services.audit_service import verify_chain
from app.utils.time import utcnow

router = APIRouter(prefix="/audit", tags=["Audit"])


def _target(entry: AuditLog) -> str:
    details = entry.details or {}
    return str(
        details.get("filename")
        or details.get("title")
        or details.get("error")
        or (f"{entry.target_type}:{entry.target_id}" if entry.target_id else entry.action)
    )


@router.get("", response_model=AuditPage)
def list_audit(
    db: Session = Depends(get_db),
    actor: str | None = None,
    action: str | None = None,
    result: str | None = None,
    target_id: str | None = Query(default=None, alias="targetId"),
    q: str | None = Query(default=None, max_length=300),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    workspace: Workspace = Depends(current_workspace),
):
    stmt = select(AuditLog).where(AuditLog.workspace_id == workspace.id)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if result:
        try:
            stmt = stmt.where(AuditLog.result == AuditResult(result))
        except ValueError:
            pass
    if target_id:
        stmt = stmt.where(AuditLog.target_id == target_id)
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                AuditLog.actor.ilike(needle),
                AuditLog.action.ilike(needle),
                AuditLog.target_id.ilike(needle),
                AuditLog.target_type.ilike(needle),
            )
        )
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    entries = list(db.scalars(stmt.order_by(AuditLog.id.desc()).limit(limit).offset(offset)).all())
    valid, _count, _broken = verify_chain(db)
    return AuditPage(
        items=[
            AuditEntryOut(
                id=entry.id,
                actor=entry.actor,
                action=entry.action,
                target=_target(entry),
                target_type=entry.target_type,
                target_id=entry.target_id,
                at=entry.created_at,
                ip=entry.ip_address,
                result=entry.result.value,
                details=entry.details or {},
                previous_hash=entry.previous_hash,
                hash=entry.entry_hash,
            )
            for entry in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
        chain_valid=valid,
    )


@router.get("/verify", response_model=AuditVerify)
def verify_audit_chain(db: Session = Depends(get_db)):
    valid, entries, broken_at = verify_chain(db)
    return AuditVerify(
        valid=valid,
        entries=entries,
        broken_at=broken_at,
        message=(
            "Audit chain is intact."
            if valid
            else "Audit chain verification failed; investigate the flagged entry immediately."
        ),
        checked_at=utcnow(),
    )
