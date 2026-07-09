from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.audit_actions import AuditAction
from app.core.audit_logger import write_audit_log
from app.core.dependencies import get_current_user, get_db, require_role
from app.core.geo_utils import coords_to_polygon
from app.core.request_utils import get_ip
from app.models.survey_record import SurveyRecord
from app.models.user import User
from app.schemas.survey import (
    SurveyAdminUpdateSchema,
    SurveyCreateSchema,
    SurveyResponse,
    SurveyVerifySchema,
)

router = APIRouter(prefix="/api/v1/surveys", tags=["Survey Records"])


def record_to_response(record: SurveyRecord) -> SurveyResponse:
    return SurveyResponse(
        id=str(record.id),
        user_id=str(record.user_id),
        village=record.village,
        plot=record.plot,
        geometry=mapping(to_shape(record.geometry)) if record.geometry is not None else None,
        timestamp=record.timestamp,
        verified_status=record.verified_status,
    )


async def get_record_or_404(db: AsyncSession, record_id: UUID) -> SurveyRecord:
    result = await db.execute(select(SurveyRecord).where(SurveyRecord.id == record_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey record not found")
    return record


def parse_uuid(value: str, label: str = "id") -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid {label}")


@router.post("", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey(
    payload: SurveyCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    target_uuid = parse_uuid(payload.user_id, "user_id")

    target_user = await db.execute(select(User).where(User.user_id == target_uuid))
    if target_user.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    record = SurveyRecord(
        user_id=target_uuid,
        village=payload.village,
        plot=payload.plot,
        geometry=from_shape(coords_to_polygon(payload.coordinates), srid=4326),
    )
    db.add(record)

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_CREATED,
        user_id=_admin.user_id,
        user_email=_admin.email,
        resource=f"user:{payload.user_id}",
        detail=f"Created survey record for user {payload.user_id}",
        ip_address=get_ip(request),
    )

    await db.commit()
    await db.refresh(record)
    return record_to_response(record)


@router.get("", response_model=List[SurveyResponse])
async def list_surveys(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
    limit: int = 50,
    offset: int = 0,
):
    query = (
        select(SurveyRecord)
        .order_by(SurveyRecord.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    records = result.scalars().all()
    return [record_to_response(record) for record in records]


@router.get("/my", response_model=List[SurveyResponse])
async def list_my_surveys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(SurveyRecord).where(SurveyRecord.user_id == user.user_id).order_by(
        SurveyRecord.timestamp.desc()
    )
    result = await db.execute(query)
    records = result.scalars().all()
    return [record_to_response(record) for record in records]


@router.get("/{record_id}", response_model=SurveyResponse)
async def get_survey(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record_uuid = parse_uuid(record_id)
    record = await get_record_or_404(db, record_uuid)

    current_role = getattr(user.role, "value", user.role)
    is_admin = current_role == "admin"
    is_self = str(user.user_id) == str(record.user_id)

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own survey records.",
        )

    return record_to_response(record)


@router.patch("/{record_id}/verify", response_model=SurveyResponse)
async def verify_survey(
    record_id: str,
    payload: SurveyVerifySchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record_uuid = parse_uuid(record_id)
    record = await get_record_or_404(db, record_uuid)

    current_role = getattr(user.role, "value", user.role)
    is_admin = current_role == "admin"
    is_self = str(user.user_id) == str(record.user_id)

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update your own survey records.",
        )

    record.verified_status = payload.verified_status

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_VERIFIED,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"survey:{record_id}",
        detail=f"Set verified_status to {payload.verified_status} for survey {record_id}",
        ip_address=get_ip(request),
    )

    await db.commit()
    await db.refresh(record)
    return record_to_response(record)


@router.put("/{record_id}", response_model=SurveyResponse)
async def admin_update_survey(
    record_id: str,
    payload: SurveyAdminUpdateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    record_uuid = parse_uuid(record_id)
    record = await get_record_or_404(db, record_uuid)

    if payload.user_id is not None:
        target_uuid = parse_uuid(payload.user_id, "user_id")
        target_user = await db.execute(select(User).where(User.user_id == target_uuid))
        if target_user.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        record.user_id = target_uuid

    if payload.village is not None:
        record.village = payload.village
    if payload.plot is not None:
        record.plot = payload.plot
    if payload.coordinates is not None:
        record.geometry = from_shape(coords_to_polygon(payload.coordinates), srid=4326)
    if payload.verified_status is not None:
        record.verified_status = payload.verified_status

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_UPDATED,
        user_id=admin.user_id,
        user_email=admin.email,
        resource=f"survey:{record_id}",
        detail=f"Updated survey record {record_id}",
        ip_address=get_ip(request),
    )

    await db.commit()
    await db.refresh(record)
    return record_to_response(record)


@router.delete("/{record_id}", status_code=status.HTTP_200_OK)
async def delete_survey(
    record_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    record_uuid = parse_uuid(record_id)
    record = await get_record_or_404(db, record_uuid)

    await db.delete(record)

    await write_audit_log(
        db=db,
        action=AuditAction.SURVEY_DELETED,
        user_id=admin.user_id,
        user_email=admin.email,
        resource=f"survey:{record_id}",
        detail=f"Deleted survey record {record_id}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": f"Survey record {record_id} deleted"}
