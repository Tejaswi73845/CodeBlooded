from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Evidence
from app.models.enums import AuditResult, IntegrityStatus
from app.services.audit_service import record_audit
from app.utils.files import file_sha256, validate_stored_path
from app.utils.logging import get_logger
from app.utils.time import utcnow

logger = get_logger(__name__)


def verify_evidence_integrity(
    db: Session,
    evidence: Evidence,
    *,
    actor: str = "System",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> IntegrityStatus:
    try:
        path = validate_stored_path(evidence.file_path)
    except ValueError:
        status = IntegrityStatus.MISMATCH
        detail = "Stored path is outside the upload root."
    else:
        if not path.exists():
            status = IntegrityStatus.MISMATCH
            detail = "Original file is missing from storage."
        else:
            actual = file_sha256(path)
            if actual.lower() == evidence.sha256.lower():
                status = IntegrityStatus.VERIFIED
                detail = "Recomputed digest matches the intake digest."
            else:
                status = IntegrityStatus.MISMATCH
                detail = f"Digest mismatch (expected {evidence.sha256[:12]}…, got {actual[:12]}…)."

    evidence.integrity_status = status
    evidence.last_verified_at = utcnow()
    db.add(evidence)
    db.commit()

    record_audit(
        db,
        actor=actor,
        action="Integrity verified" if status == IntegrityStatus.VERIFIED else "Integrity verification failed",
        target_type="evidence",
        target_id=str(evidence.id),
        result=AuditResult.SUCCESS if status == IntegrityStatus.VERIFIED else AuditResult.WARNING,
        details={"sha256": evidence.sha256, "status": status.value, "detail": detail},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    logger.info("Integrity %s for evidence %s", status.value, evidence.id)
    return status
