from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def write_audit_log(
    db: AsyncSession,
    action: str,
    success: bool = True,
    user_id=None,
    user_email: str = None,
    resource: str = None,
    detail: str = None,
    ip_address: str = None,
):
    log = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource=resource,
        detail=detail,
        ip_address=ip_address,
        success=success,
    )
    db.add(log)
