from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    target_type: str,
    target_id: str | None,
    actor_user_id: int | None,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        target_type=target_type,
        target_id=target_id,
        actor_user_id=actor_user_id,
        details=details or {},
    )
    db.add(entry)
    return entry
