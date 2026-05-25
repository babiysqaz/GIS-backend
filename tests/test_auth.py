import pytest
from httpx import AsyncClient
from jose import jwt
from app.config import settings


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    payload = jwt.decode(
        data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert payload.get("role") == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    payload = jwt.decode(
        resp.json()["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert payload.get("role") == "admin"


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"}
    )
    assert resp.status_code == 401
