import datetime

from pydantic import BaseModel

from app.models.user import UserRole


class UserLogin(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
