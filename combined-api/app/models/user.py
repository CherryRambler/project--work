import uuid
import enum

from sqlalchemy import Column, String, Boolean, TIMESTAMP, Enum, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.db.session import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    viewer = "viewer"

class AccountStatusEnum(str, enum.Enum):
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"

class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone_no = Column(String(20), unique=True, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.viewer)
    hashed_password = Column(String, nullable=False)
    account_status = Column(Enum(AccountStatusEnum), default=AccountStatusEnum.ACTIVATED, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
