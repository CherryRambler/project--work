# app/core/audit_logger.py
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def write_audit_log(
    db: AsyncSession,
    action: str,
    success: bool = True,
    user_id: Optional[Any] = None,
    user_email: Optional[str] = None,
    resource: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
    survey_record_id: Optional[Any] = None,
    change_type: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        change_type=change_type,
        resource=resource,
        survey_record_id=survey_record_id,
        changes=changes,
        detail=detail,
        ip_address=ip_address,
        success=success,
    )
    db.add(log)