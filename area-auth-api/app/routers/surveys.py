# app/routers/surveys.py  — full updated version with structured audit logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_actions import AuditAction
from app.core.audit_logger import write_audit_log
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.audit_log import AuditLog
from app.models.survey_record import SurveyRecord
from app.models.user import User
from app.schemas.survey import (
    SurveyAdminUpdateSchema,
    SurveyCreateSchema,
    SurveyResponse,
    SurveyVerifySchema,
)

router = APIRouter(prefix="/api/v1/surveys", tags=["Survey Records"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def coords_to_polygon(coordinates: list):
    ring = coordinates[:]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return shape({"type": "Polygon", "coordinates": [ring]})


def record_to_response(record: SurveyRecord) -> SurveyResponse:
    return SurveyResponse(
        id=str(record.id),
        user_id=str(record.user_id),
        village=record.village,
        plot=record.plot,
        geometry=mapping(to_shape(record.geometry)) if record.geometry else None,
        timestamp=record.timestamp,
        verified_status=record.verified_status,
    )


async def get_record_by_id(
    db: AsyncSession, record_id: UUID
) -> Optional[SurveyRecord]:
    result = await db.execute(
        select(SurveyRecord).where(SurveyRecord.id == record_id)
    )
    return result.scalar_one_or_none()


# ── CREATE — Admin only ───────────────────────────────────────────────────────

@router.post("", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey_record(
    payload: SurveyCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    """Admin creates a new survey record and assigns it to a specific user."""
    try:
        target_uuid = UUID(payload.user_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid user_id")

    target = await db.execute(select(User).where(User.user_id == target_uuid))
    if target.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target user not found")

    record = SurveyRecord(
        user_id=target_uuid,
        geometry=from_shape(coords_to_polygon(payload.coordinates), srid=4326),
        village=payload.village,
        plot=payload.plot,
        verified_status=False,
    )
    db.add(record)
    await db.flush()  # get record.id before writing audit log

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_CREATED,
        change_type="CREATE",
        user_id=admin.user_id,
        user_email=admin.email,
        resource=f"survey:{record.id}",
        survey_record_id=record.id,
        changes={
            "fields": ["user_id", "village", "plot", "geometry", "verified_status"],
            "new": {
                "user_id": payload.user_id,
                "village": payload.village,
                "plot": payload.plot,
                "verified_status": False,
            },
        },
        detail=f"Admin created survey record for user {payload.user_id} — village={payload.village}, plot={payload.plot}",
        ip_address=get_ip(request),
    )

    await db.commit()
    await db.refresh(record)
    return record_to_response(record)


# ── LIST ALL — Admin only ─────────────────────────────────────────────────────

@router.get("", response_model=List[SurveyResponse])
async def list_all_survey_records(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
    limit: int = 50,
    offset: int = 0,
):
    """Admin retrieves all survey records across all users, paginated."""
    result = await db.execute(
        select(SurveyRecord)
        .order_by(SurveyRecord.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    return [record_to_response(r) for r in result.scalars().all()]


# ── LIST OWN — Authenticated ──────────────────────────────────────────────────

@router.get("/my", response_model=List[SurveyResponse])
async def list_my_survey_records(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    """Any authenticated user retrieves only their own survey records."""
    result = await db.execute(
        select(SurveyRecord)
        .where(SurveyRecord.user_id == user.user_id)
        .order_by(SurveyRecord.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    return [record_to_response(r) for r in result.scalars().all()]


# ── GET AUDIT LOGS FOR ONE SURVEY RECORD — Admin only ────────────────────────

@router.get("/{record_id}/audit")
async def get_survey_audit_logs(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
    change_type: Optional[str] = Query(None, description="Filter by change_type e.g. VERIFY, UPDATE, CREATE"),
    limit: int = 50,
    offset: int = 0,
):
    """
    Admin retrieves the full audit history for a specific survey record.
    Optionally filter by change_type.
    """
    try:
        record_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid record_id")

    record = await get_record_by_id(db, record_uuid)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey record not found")

    query = (
        select(AuditLog)
        .where(AuditLog.survey_record_id == record_uuid)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if change_type:
        query = query.where(AuditLog.change_type == change_type.upper())

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "action": log.action,
            "change_type": log.change_type,
            "user_id": str(log.user_id) if log.user_id else None,
            "user_email": log.user_email,
            "changes": log.changes,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "success": log.success,
            "created_at": log.created_at,
        }
        for log in logs
    ]


# ── GET ONE — Self or Admin ───────────────────────────────────────────────────

@router.get("/{record_id}", response_model=SurveyResponse)
async def get_survey_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve a single survey record. Viewers can only access their own."""
    try:
        record_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid record_id")

    record = await get_record_by_id(db, record_uuid)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey record not found")

    current_role = getattr(user.role, "value", user.role)
    is_admin = current_role == "admin"
    is_self = str(record.user_id) == str(user.user_id)

    if not is_admin and not is_self:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Access denied. You can only view your own survey records.",
        )

    return record_to_response(record)


# ── VERIFY — Self or Admin ────────────────────────────────────────────────────

@router.patch("/{record_id}/verify", response_model=SurveyResponse)
async def verify_survey_record(
    record_id: str,
    payload: SurveyVerifySchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Assigned user (or admin) toggles verified_status.
    Both true→false and false→true are allowed.
    """
    try:
        record_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid record_id")

    record = await get_record_by_id(db, record_uuid)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey record not found")

    current_role = getattr(user.role, "value", user.role)
    is_admin = current_role == "admin"
    is_self = str(record.user_id) == str(user.user_id)

    if not is_admin and not is_self:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Access denied. You can only update verification status on your own records.",
        )

    old_status = record.verified_status
    record.verified_status = payload.verified_status

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_VERIFIED,
        change_type="VERIFY",
        user_id=user.user_id,
        user_email=user.email,
        resource=f"survey:{record.id}",
        survey_record_id=record.id,
        changes={
            "field": "verified_status",
            "old": old_status,
            "new": payload.verified_status,
        },
        detail=f"verified_status changed from {old_status} to {payload.verified_status}",
        ip_address=get_ip(request),
    )

    await db.commit()
    await db.refresh(record)
    return record_to_response(record)


# ── ADMIN UPDATE — Admin only ─────────────────────────────────────────────────

@router.put("/{record_id}", response_model=SurveyResponse)
async def admin_update_survey_record(
    record_id: str,
    payload: SurveyAdminUpdateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    """Admin updates any field on any survey record with full before/after tracking."""
    try:
        record_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid record_id")

    record = await get_record_by_id(db, record_uuid)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey record not found")

    old_values = {}
    new_values = {}
    changes = []

    if payload.village is not None:
        old_values["village"] = record.village
        record.village = payload.village
        new_values["village"] = payload.village
        changes.append("village")

    if payload.plot is not None:
        old_values["plot"] = record.plot
        record.plot = payload.plot
        new_values["plot"] = payload.plot
        changes.append("plot")

    if payload.coordinates is not None:
        old_values["geometry"] = "(polygon — see previous audit entry)"
        record.geometry = from_shape(
            coords_to_polygon(payload.coordinates), srid=4326
        )
        new_values["geometry"] = payload.coordinates
        changes.append("geometry")

    if payload.verified_status is not None:
        old_values["verified_status"] = record.verified_status
        record.verified_status = payload.verified_status
        new_values["verified_status"] = payload.verified_status
        changes.append("verified_status")

    if payload.user_id is not None:
        try:
            new_user_uuid = UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid user_id")
        target = await db.execute(select(User).where(User.user_id == new_user_uuid))
        if target.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Target user not found")
        old_values["user_id"] = str(record.user_id)
        record.user_id = new_user_uuid
        new_values["user_id"] = payload.user_id
        changes.append("user_id")

    if not changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

    # Classify change type for better filtering
    if changes == ["verified_status"]:
        change_type = "STATUS_CHANGE"
    elif "user_id" in changes:
        change_type = "ASSIGN"
    else:
        change_type = "UPDATE"

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_UPDATED,
        change_type=change_type,
        user_id=admin.user_id,
        user_email=admin.email,
        resource=f"survey:{record.id}",
        survey_record_id=record.id,
        changes={
            "fields": changes,
            "old": old_values,
            "new": new_values,
        },
        detail=f"Admin updated fields: {', '.join(changes)}",
        ip_address=get_ip(request),
    )

    await db.commit()
    await db.refresh(record)
    return record_to_response(record)



@router.delete("/{record_id}", status_code=status.HTTP_200_OK)
async def delete_survey_record(
    record_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    try:
        record_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid record_id")

    record = await get_record_by_id(db, record_uuid)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey record not found")

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_DELETED,
        change_type="DELETE",
        user_id=admin.user_id,
        user_email=admin.email,
        resource=f"survey:{record.id}",
        survey_record_id=record.id,
        changes={
            "snapshot": {
                "user_id": str(record.user_id),
                "village": record.village,
                "plot": record.plot,
                "verified_status": record.verified_status,
            }
        },
        detail=f"Admin deleted survey record — village={record.village}, plot={record.plot}, assigned_user={record.user_id}",
        ip_address=get_ip(request),
    )

    await db.flush()
    await db.delete(record)
    await db.commit()
    return {"message": f"Survey record {record_id} deleted successfully"}