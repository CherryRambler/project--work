from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.audit_actions import AuditAction
from app.core.audit_logger import write_audit_log
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.audit_log import AuditLog
from app.models.authorized_area import AuthorizedArea
from app.models.user import User
from app.schemas.area import AreaAssignSchema, PointCheckSchema, UserAreaResponse

router = APIRouter(prefix="/api/v1/areas", tags=["Authorized Areas"])


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


async def get_area_for_user(db: AsyncSession, user_id: UUID) -> Optional[AuthorizedArea]:
    result = await db.execute(
        select(AuthorizedArea).where(AuthorizedArea.user_id == user_id)
    )
    return result.scalar_one_or_none()


@router.put("/users/{user_id}", response_model=UserAreaResponse)
async def assign_user_area(
    user_id: str,
    payload: AreaAssignSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        target_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid user_id")

    current_role = getattr(user.role, "value", user.role)
    is_admin = current_role == "admin"
    is_self = str(user.user_id) == str(target_uuid)

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only manage your own area.",
        )

    target_user = await db.execute(select(User).where(User.user_id == target_uuid))
    if target_user.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    area = await get_area_for_user(db, target_uuid)
    if area is None:
        area = AuthorizedArea(user_id=target_uuid)
        db.add(area)

    area.authorized_area = from_shape(coords_to_polygon(payload.coordinates), srid=4326)

    await write_audit_log(
        db=db,
        action=AuditAction.ASSIGN_USER_AREA,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"user:{user_id}",
        detail=f"Assigned authorized area to user {user_id}",
        ip_address=get_ip(request),
    )

    await db.commit()
    await db.refresh(area)

    return UserAreaResponse(
        user_id=str(area.user_id),
        has_area=True,
        area=mapping(to_shape(area.authorized_area)),
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def remove_user_area(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        target_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid user_id")

    current_role = getattr(user.role, "value", user.role)
    is_admin = current_role == "admin"
    is_self = str(user.user_id) == str(target_uuid)

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only manage your own area.",
        )

    area = await get_area_for_user(db, target_uuid)

    if area is None or area.authorized_area is None:
        return {"message": "User has no area assigned"}

    area.authorized_area = None

    await write_audit_log(
        db=db,
        action=AuditAction.REMOVE_USER_AREA,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"user:{user_id}",
        detail=f"Removed authorized area from user {user_id}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": f"Area removed from user {user_id}"}


@router.get("/users/{user_id}", response_model=UserAreaResponse)
async def get_user_area(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        target_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid user_id")

    current_role = getattr(user.role, "value", user.role)
    is_admin = current_role == "admin"
    is_self = str(user.user_id) == str(target_uuid)

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own area.",
        )

    area = await get_area_for_user(db, target_uuid)

    return UserAreaResponse(
        user_id=user_id,
        has_area=area is not None and area.authorized_area is not None,
        area=mapping(to_shape(area.authorized_area)) if area and area.authorized_area else None,
    )


@router.post("/check-point")
async def check_point(
    payload: PointCheckSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    area = await get_area_for_user(db, user.user_id)

    if area is None or area.authorized_area is None:
        await write_audit_log(
            db=db,
            action=AuditAction.CHECK_POINT,
            user_id=user.user_id,
            user_email=user.email,
            resource=f"point:{payload.latitude},{payload.longitude}",
            detail="Check attempted but user has no area assigned",
            ip_address=get_ip(request),
            success=False,
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No authorized area assigned to this user",
        )

    point_wkt = f"POINT({payload.longitude} {payload.latitude})"

    result = await db.execute(
        select(
            func.ST_Contains(
                AuthorizedArea.authorized_area,
                func.ST_GeomFromText(point_wkt, 4326),
            )
        ).where(AuthorizedArea.user_id == user.user_id)
    )
    inside = result.scalar()

    await write_audit_log(
        db=db,
        action=AuditAction.CHECK_POINT,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"point:{payload.latitude},{payload.longitude}",
        detail="Point inside authorized area" if inside else "Point outside authorized area",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"inside": bool(inside)}


@router.get("/audit", tags=["Audit Logs"])
async def list_area_audit_logs(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
    limit: int = 50,
    offset: int = 0,
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()