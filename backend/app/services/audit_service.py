from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditLog
from app.models.enums import AuditResult
from app.utils.time import utcnow

_audit_lock = threading.Lock()


def _canonical_details(details: dict[str, Any] | None) -> str:
    return json.dumps(details or {}, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(
    *,
    previous_hash: str,
    created_at,
    actor: str,
    action: str,
    target_type: str,
    target_id: str | None,
    result: str,
    details: dict[str, Any] | None,
) -> str:
    payload = "|".join(
        [
            previous_hash,
            created_at.isoformat(timespec="microseconds"),
            actor,
            action,
            target_type,
            target_id or "",
            result,
            _canonical_details(details),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    target_type: str = "system",
    target_id: str | None = None,
    result: AuditResult = AuditResult.SUCCESS,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    workspace_id=None,
) -> AuditLog:
    """Append an chained audit entry. The lock keeps the chain ordered in-process."""
    with _audit_lock:
        last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
        previous_hash = last.entry_hash if last else settings.audit_genesis_hash
        created_at = utcnow()
        entry_hash = compute_entry_hash(
            previous_hash=previous_hash,
            created_at=created_at,
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result.value,
            details=details,
        )
        entry = AuditLog(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            workspace_id=workspace_id,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
            created_at=created_at,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry


def verify_chain(db: Session) -> tuple[bool, int, int | None]:
    entries = db.scalars(select(AuditLog).order_by(AuditLog.id.asc())).all()
    previous = settings.audit_genesis_hash
    for index, entry in enumerate(entries, start=1):
        expected = compute_entry_hash(
            previous_hash=previous,
            created_at=entry.created_at,
            actor=entry.actor,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            result=entry.result.value,
            details=entry.details,
        )
        if entry.previous_hash != previous or entry.entry_hash != expected:
            return False, len(entries), index
        previous = entry.entry_hash
    return True, len(entries), None


def audit_count(db: Session) -> int:
    return int(db.scalar(select(func.count(AuditLog.id))) or 0)
