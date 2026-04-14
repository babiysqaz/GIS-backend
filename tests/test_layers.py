import pytest
from httpx import AsyncClient


LAYER_PAYLOAD = {
    "name": "測試圖層",
    "description": "一個測試用的圖層",
    "service_url": "https://services.arcgis.com/example/FeatureServer/0",
    "layer_type": "feature",
    "visible": True,
    "opacity": 0.8,
    "sort_order": 1,
}


@pytest.mark.asyncio
async def test_list_layers_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/layers/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_layers_empty(client: AsyncClient, user_token: str):
    resp = await client.get(
        "/api/v1/layers/", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_layer_as_admin(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == LAYER_PAYLOAD["name"]
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_create_layer_forbidden_for_user(client: AsyncClient, user_token: str):
    resp = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_layer(client: AsyncClient, admin_token: str):
    create = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    layer_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/layers/{layer_id}",
        json={"name": "更新後的名稱", "opacity": 0.5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新後的名稱"
    assert resp.json()["opacity"] == 0.5


@pytest.mark.asyncio
async def test_update_layer_not_found(client: AsyncClient, admin_token: str):
    resp = await client.patch(
        "/api/v1/layers/9999",
        json={"name": "不存在"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_layer(client: AsyncClient, admin_token: str, user_token: str):
    create = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    layer_id = create.json()["id"]

    resp = await client.delete(
        f"/api/v1/layers/{layer_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204

    list_resp = await client.get(
        "/api/v1/layers/", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_layer_not_found(client: AsyncClient, admin_token: str):
    resp = await client.delete(
        "/api/v1/layers/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
