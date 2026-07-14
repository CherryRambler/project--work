from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from uuid import UUID
from typing import Optional, Union

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.authorized_area import AuthorizedArea
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.core.config import settings
from app.core.audit_logger import write_audit_log
from app.core.audit_actions import AuditAction
from app.core.request_utils import get_ip
from app.models.user import User, RoleEnum, AccountStatusEnum
from app.models.session import UserSession
from app.schemas.auth import (
    RegisterSchema,
    LoginSchema,
    UpdateMeSchema,
    PasswordChangeSchema,
    RefreshTokenSchema,
    TokenResponseSchema,
    LogoutSchema,
    AccountStatusUpdateSchema,
    UserProfileResponse,
    UserListItemResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=5)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: Union[str, UUID]) -> Optional[User]:
    try:
        user_uuid = user_id if isinstance(user_id, UUID) else UUID(user_id)
    except ValueError:
        return None

    result = await db.execute(select(User).where(User.user_id == user_uuid))
    return result.scalar_one_or_none()


# ── REGISTER ─────────────────────────────────────────────────────
@router.post("/register")
async def register(data: RegisterSchema, request: Request, db: AsyncSession = Depends(get_db)):
    if await get_user_by_email(db, data.email):
        raise HTTPException(400, "Email already registered")

    existing_username = await db.execute(select(User).where(User.user_name == data.user_name))
    if existing_username.scalar_one_or_none():
        raise HTTPException(400, "Username already taken")

    existing_phone = await db.execute(select(User).where(User.phone_no == data.phone_no))
    if existing_phone.scalar_one_or_none():
        raise HTTPException(400, "Phone number already registered")

    try:
        role = RoleEnum(data.role)
    except ValueError:
        raise HTTPException(
            400,
            f"Invalid role '{data.role}'. Must be one of: {[r.value for r in RoleEnum]}"
        )

    user = User(
        user_name=data.user_name,
        email=data.email,
        phone_no=data.phone_no,
        hashed_password=hash_password(data.password),
        role=role,
    )

    db.add(user)
    await db.flush()

    await write_audit_log(
        db=db,
        action=AuditAction.REGISTER,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"user:{user.user_id}",
        detail=f"New user registered with role: {user.role}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": "User created"}

# ── LOGIN ─────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponseSchema)
async def login(data: LoginSchema, request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, data.email)

    if not user:
        await write_audit_log(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_email=data.email,
            detail="User not found",
            ip_address=get_ip(request),
            success=False,
        )
        await db.commit()
        raise HTTPException(401, "Invalid credentials")

    if user.account_status != AccountStatusEnum.ACTIVATED:
        await write_audit_log(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=user.user_id,
            user_email=user.email,
            detail="Account is disabled",
            ip_address=get_ip(request),
            success=False,
        )
        await db.commit()
        raise HTTPException(403, "Account is disabled")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        remaining_seconds = (user.locked_until - now).total_seconds()
        remaining_minutes = int(remaining_seconds / 60) + 1

        await write_audit_log(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=user.user_id,
            user_email=user.email,
            detail=f"Login attempted on locked account. Unlocks in {remaining_minutes} minute(s)",
            ip_address=get_ip(request),
            success=False,
        )
        await db.commit()
        raise HTTPException(
            403,
            f"Account locked due to too many failed attempts. Try again in {remaining_minutes} minute(s)",
        )

    if not verify_password(data.password, user.hashed_password):
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
            user.failed_login_attempts = 0

            await write_audit_log(
                db=db,
                action=AuditAction.ACCOUNT_LOCKED,
                user_id=user.user_id,
                user_email=user.email,
                detail=f"Account locked for {LOCKOUT_DURATION.seconds // 60} minutes after {MAX_FAILED_ATTEMPTS} failed attempts",
                ip_address=get_ip(request),
                success=False,
            )
            await db.commit()
            raise HTTPException(
                403,
                f"Too many failed attempts. Account locked for {LOCKOUT_DURATION.seconds // 60} minutes",
            )

        attempts_left = MAX_FAILED_ATTEMPTS - user.failed_login_attempts

        await write_audit_log(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=user.user_id,
            user_email=user.email,
            detail=f"Wrong password. {attempts_left} attempt(s) remaining before lockout",
            ip_address=get_ip(request),
            success=False,
        )
        await db.commit()
        raise HTTPException(
            401,
            f"Invalid credentials. {attempts_left} attempt(s) remaining before lockout",
        )

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None

    # Create tokens
    access = create_access_token(
        str(user.user_id),
        str(user.role.value),
        user.account_status == AccountStatusEnum.ACTIVATED,
    )
    refresh = create_refresh_token(str(user.user_id))

    # Create session object
    session = UserSession(
        user_id=user.user_id,
        refresh_token=refresh,
        platform=data.platform,
        ip_address=get_ip(request),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)

    await write_audit_log(
        db=db,
        action=AuditAction.LOGIN_SUCCESS,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"user:{user.user_id}",
        detail=f"Login from {data.platform}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"access_token": access, "refresh_token": refresh}

# ── REFRESH ─────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh_token(data: RefreshTokenSchema, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(
            data.refresh_token,
            settings.REFRESH_TOKEN_SECRET,
            algorithms=[settings.ALGORITHM],
        )

        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")

    except JWTError:
        raise HTTPException(401, "Invalid token")

    # Look up the session WITHOUT filtering by is_active first,
    # so we can distinguish "already used" from "never existed"
    result = await db.execute(
        select(UserSession).where(UserSession.refresh_token == data.refresh_token)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(401, "Session not found or already logged out")

    # REUSE DETECTION: if this token was already rotated away from,
    # someone is trying to use a stale/stolen token. Revoke every
    # active session for this user as a precaution.
    if not session.is_active:
        all_sessions = await db.execute(
            select(UserSession).where(UserSession.user_id == session.user_id)
        )
        for s in all_sessions.scalars().all():
            s.is_active = False

        await write_audit_log(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=session.user_id,
            detail="Refresh token reuse detected — all sessions revoked",
            ip_address=get_ip(request),
            success=False,
        )
        await db.commit()
        raise HTTPException(401, "Token reuse detected. All sessions have been revoked. Please log in again.")

    if session.expires_at < datetime.now(timezone.utc):
        session.is_active = False
        await db.commit()
        raise HTTPException(401, "Session expired, please log in again")

    user = await get_user_by_id(db, session.user_id)

    if not user or user.account_status != AccountStatusEnum.ACTIVATED:
        session.is_active = False
        await db.commit()
        raise HTTPException(401, "User does not exist or is disabled")

    # ROTATION: invalidate the old refresh token...
    session.is_active = False

    new_access = create_access_token(
        str(user.user_id),
        str(user.role.value),
        user.account_status == AccountStatusEnum.ACTIVATED,
    )
    new_refresh = create_refresh_token(str(user.user_id))

    new_session = UserSession(
        user_id=user.user_id,
        refresh_token=new_refresh,
        platform=session.platform,
        ip_address=get_ip(request),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_session)

    await write_audit_log(
        db=db,
        action=AuditAction.REFRESH_TOKEN,
        user_id=session.user_id,
        user_email=user.email,
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"access_token": new_access, "refresh_token": new_refresh}

# ── LOGOUT ─────────────────────────────────────────────────────
@router.post("/logout")
async def logout(
    data: LogoutSchema,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.refresh_token == data.refresh_token,
            UserSession.user_id == user.user_id,
            UserSession.is_active.is_(True),
        )
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(404, "Session not found or already logged out")

    session.is_active = False

    await write_audit_log(
        db=db,
        action=AuditAction.LOGOUT,
        user_id=user.user_id,
        user_email=user.email,
        detail="Logged out from current session",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": "Logged out successfully"}


# ── LOGOUT ALL ─────────────────────────────────────────────────────
@router.post("/logout-all")
async def logout_all(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user.user_id,
            UserSession.is_active.is_(True),
        )
    )
    sessions = result.scalars().all()

    for s in sessions:
        s.is_active = False

    await write_audit_log(
        db=db,
        action=AuditAction.LOGOUT,
        user_id=user.user_id,
        user_email=user.email,
        detail=f"Logged out from all {len(sessions)} active sessions",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": f"Logged out from {len(sessions)} devices"}


# ── LIST SESSIONS ─────────────────────────────────────────────────────
@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user.user_id,
            UserSession.is_active.is_(True),
        )
    )
    sessions = result.scalars().all()

    return [
        {
            "session_id": str(s.id),
            "platform": s.platform,
            "ip_address": s.ip_address,
            "last_used_at": s.last_used_at,
            "created_at": s.created_at,
        }
        for s in sessions
    ]


# ── UNLOCK ACCOUNT ─────────────────────────────────────────────────────
@router.post("/unlock/{user_id}")
async def unlock_account(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    target_user = await get_user_by_id(db, user_id)

    if not target_user:
        raise HTTPException(404, "User not found")

    if not target_user.locked_until:
        return {"message": "Account is not locked"}

    target_user.locked_until = None
    target_user.failed_login_attempts = 0

    await write_audit_log(
        db=db,
        action=AuditAction.ACCOUNT_UNLOCKED,
        user_id=admin.user_id,
        user_email=admin.email,
        resource=f"user:{user_id}",
        detail=f"Admin manually unlocked account of {target_user.email}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": f"Account {target_user.email} has been unlocked"}


# ── UPDATE ACCOUNT STATUS ─────────────────────────────────────────────
@router.put("/users/{user_id}/status")
async def update_account_status(
    user_id: str,
    data: AccountStatusUpdateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    target_user = await get_user_by_id(db, user_id)

    if not target_user:
        raise HTTPException(404, "User not found")

    if str(target_user.user_id) == str(admin.user_id):
        raise HTTPException(400, "Admins cannot change their own account status here")

    target_user.account_status = data.account_status

    action = (
        AuditAction.ACCOUNT_ACTIVATED
        if data.account_status == AccountStatusEnum.ACTIVATED
        else AuditAction.ACCOUNT_DEACTIVATED
    )

    await write_audit_log(
        db=db,
        action=action,
        user_id=admin.user_id,
        user_email=admin.email,
        resource=f"user:{target_user.user_id}",
        detail=f"Admin set account_status to {data.account_status} for {target_user.email}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": f"Account status for {target_user.email} updated to {data.account_status}"}


# ── LIST USERS (admin) ────────────────────────────────────────────────────────
@router.get("/users", response_model=list[UserListItemResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
    limit: int = 50,
    offset: int = 0,
):
    """Return all users with basic profile and whether they have an area assigned.
    Admins use this to look up user UUIDs before calling the area-assignment API."""
    result = await db.execute(
        select(User, AuthorizedArea)
        .outerjoin(AuthorizedArea, User.user_id == AuthorizedArea.user_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()

    return [
        UserListItemResponse(
            user_id=str(user.user_id),
            user_name=user.user_name,
            email=user.email,
            role=user.role,
            account_status=user.account_status,
            has_area=area is not None and area.authorized_area is not None,
        )
        for user, area in rows
    ]


# ── ME ─────────────────────────────────────────────────────
@router.get("/me", response_model=UserProfileResponse)
async def me(user: User = Depends(get_current_user)):
    return UserProfileResponse(
        user_id=str(user.user_id),
        user_name=user.user_name,
        email=user.email,
        phone_no=user.phone_no,
        role=user.role,
        account_status=user.account_status,
        created_at=user.created_at,
    )


# ── UPDATE ME ─────────────────────────────────────────────────────
@router.put("/me")
async def update_me(
    data: UpdateMeSchema,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    changes = []

    if data.phone_no:
        user.phone_no = data.phone_no
        changes.append("phone_no")

    if not changes:
        raise HTTPException(400, "No fields to update")

    await write_audit_log(
        db=db,
        action=AuditAction.UPDATE_PROFILE,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"user:{user.user_id}",
        detail=f"Updated fields: {', '.join(changes)}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": "Updated"}


# ── CHANGE PASSWORD ─────────────────────────────────────────────────────
@router.put("/me/password")
async def change_password(
    data: PasswordChangeSchema,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, user.hashed_password):
        await write_audit_log(
            db=db,
            action=AuditAction.PASSWORD_CHANGE,
            user_id=user.user_id,
            user_email=user.email,
            detail="Wrong current password",
            ip_address=get_ip(request),
            success=False,
        )
        await db.commit()
        raise HTTPException(401, "Wrong password")

    user.hashed_password = hash_password(data.new_password)

    await write_audit_log(
        db=db,
        action=AuditAction.PASSWORD_CHANGE,
        user_id=user.user_id,
        user_email=user.email,
        resource=f"user:{user.user_id}",
        ip_address=get_ip(request),
    )

    await db.commit()
    return {"message": "Password updated"}