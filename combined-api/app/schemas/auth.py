from pydantic import BaseModel, EmailStr, field_validator
import re
from typing import Optional
from app.models.user import AccountStatusEnum


class AccountStatusUpdateSchema(BaseModel):
    account_status: AccountStatusEnum


def validate_strong_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', v):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', v):
        raise ValueError('Password must contain at least one number')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError('Password must contain at least one special character')
    return v


class RegisterSchema(BaseModel):
    user_name: str
    email: EmailStr
    phone_no: str
    password: str
    role: Optional[str] = "viewer"      

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_strong_password(v)


class LoginSchema(BaseModel):
    email: EmailStr
    password: str
    platform: str = "web"


class UpdateMeSchema(BaseModel):
    phone_no: Optional[str] = None


class PasswordChangeSchema(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_strong_password(v)


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


class AccessTokenResponseSchema(BaseModel):
    access_token: str


class LogoutSchema(BaseModel):
    refresh_token: str