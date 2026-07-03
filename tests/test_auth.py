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
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["tokenType"] == "bearer"
    payload = jwt.decode(data["accessToken"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
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
    refresh_token = login.json()["refreshToken"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "accessToken" in resp.json()
    payload = jwt.decode(
        resp.json()["accessToken"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert payload.get("role") == "admin"


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_reuse_detected(client: AsyncClient, admin_user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    refresh_token = login.json()["refreshToken"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200

    # Second use of same token triggers reuse detection
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_new_refresh_token_revoked_after_reuse_detection(client: AsyncClient, admin_user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    old_refresh_token = login.json()["refreshToken"]

    rotate = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    new_refresh_token = rotate.json()["refreshToken"]

    # Attacker replays the old token — triggers reuse detection + revokes ALL tokens
    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})

    # The new (legitimate) token should also be revoked now
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_access_token_rejected_as_refresh(client: AsyncClient, admin_user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    access_token = login.json()["accessToken"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
