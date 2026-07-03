import datetime
import uuid
from typing import Any

from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict[str, Any], expires_delta: datetime.timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.datetime.now(datetime.UTC) + expires_delta
    payload["jti"] = str(uuid.uuid4())
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: dict[str, Any]) -> str:
    return _create_token(
        {**data, "type": "access"},
        datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    return _create_token(
        {**data, "type": "refresh"},
        datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def _decode_token(token: str, expected_type: str) -> int:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def verify_access_token(token: str) -> int:
    return _decode_token(token, "access")


def verify_refresh_token(token: str) -> int:
    return _decode_token(token, "refresh")


async def store_refresh_token(db: AsyncSession, user_id: int, token: str) -> None:
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    record = RefreshToken(
        user_id=user_id,
        token_hash=RefreshToken.hash_token(token),
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()


async def consume_refresh_token(db: AsyncSession, token: str) -> int:
    """
    Validates refresh token and marks it as used.
    If token was already used (reuse detected), revokes ALL tokens for that user.
    """
    verify_refresh_token(token)  # raises 401 if JWT invalid or wrong type

    token_hash = RefreshToken.hash_token(token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    now = datetime.datetime.now(datetime.UTC)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.UTC)

    if expires_at < now:
        raise HTTPException(status_code=401, detail="Refresh token expired")

    if record.is_used:
        # Token reuse detected — attacker may have stolen the token; revoke everything
        await revoke_all_refresh_tokens(db, record.user_id)
        raise HTTPException(status_code=401, detail="Refresh token already used")

    record.is_used = True
    await db.commit()
    return record.user_id


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_used == False)  # noqa: E712
        .values(is_used=True)
    )
    await db.commit()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
