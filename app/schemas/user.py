import datetime

from app.models.user import UserRole
from app.schemas.common import BaseAPIModel


class UserLogin(BaseAPIModel):
    email: str
    password: str


class RefreshRequest(BaseAPIModel):
    refresh_token: str


class TokenResponse(BaseAPIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseAPIModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime.datetime
