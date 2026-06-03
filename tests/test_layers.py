import pytest
from httpx import AsyncClient

from app.services import layer_service

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
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_layers_empty(client: AsyncClient, user_token: str):
    resp = await client.get(
        "/api/v1/layers/", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_layer_as_admin(client: AsyncClient, admin_token: str, monkeypatch):
    async def fake_fetch(service_url: str):
        return [
            {
                "layerId": 0,
                "layerName": "測試圖層",
                "layerType": None,
                "minScale": None,
                "maxScale": None,
                "legend": [],
            }
        ]

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch)

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
async def test_create_layer_fetches_legend(client: AsyncClient, admin_token: str, monkeypatch):
    fake_legend = [
        {
            "layerId": 0,
            "layerName": "測試圖層",
            "layerType": None,
            "minScale": None,
            "maxScale": None,
            "legend": [
                {
                    "label": "測試",
                    "url": None,
                    "imageData": "fakeImageData",
                    "contentType": "image/png",
                    "height": 20,
                    "width": 20,
                }
            ],
        }
    ]

    async def fake_fetch(service_url: str):
        return fake_legend

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch)

    resp = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["legend"] == fake_legend


@pytest.mark.asyncio
async def test_update_layer_refreshes_legend(client: AsyncClient, admin_token: str, monkeypatch):
    fake_legend = [
        {
            "layerId": 0,
            "layerName": "測試圖層",
            "layerType": None,
            "minScale": None,
            "maxScale": None,
            "legend": [
                {
                    "label": "測試",
                    "url": None,
                    "imageData": "fakeImageData",
                    "contentType": "image/png",
                    "height": 20,
                    "width": 20,
                }
            ],
        }
    ]

    async def fake_fetch(service_url: str):
        return fake_legend

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch)

    create = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    layer_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/layers/{layer_id}",
        json={"name": "更新後的名稱"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["legend"] == fake_legend


@pytest.mark.asyncio
async def test_create_layer_forbidden_for_user(client: AsyncClient, user_token: str):
    resp = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_layer(client: AsyncClient, admin_token: str, monkeypatch):
    async def fake_fetch(service_url: str):
        return [
            {
                "layerId": 0,
                "layerName": "測試圖層",
                "layerType": None,
                "minScale": None,
                "maxScale": None,
                "legend": [],
            }
        ]

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch)

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
async def test_delete_layer(client: AsyncClient, admin_token: str, user_token: str, monkeypatch):
    async def fake_fetch(service_url: str):
        return [
            {
                "layerId": 0,
                "layerName": "測試圖層",
                "layerType": None,
                "minScale": None,
                "maxScale": None,
                "legend": [],
            }
        ]

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch)

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


@pytest.mark.asyncio
async def test_create_layer_ssl_error_returns_400(
    client: AsyncClient, admin_token: str, monkeypatch
):
    async def fake_fetch(service_url: str):
        raise ValueError(
            "服務的 SSL 憑證驗證失敗，無法新增此圖層：[SSL: CERTIFICATE_VERIFY_FAILED]"
        )

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch)

    resp = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "SSL" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_layer_ssl_error_returns_400(
    client: AsyncClient, admin_token: str, monkeypatch
):
    async def fake_fetch_ok(service_url: str):
        return [
            {
                "layerId": 0,
                "layerName": "測試圖層",
                "layerType": None,
                "minScale": None,
                "maxScale": None,
                "legend": [],
            }
        ]

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch_ok)
    create = await client.post(
        "/api/v1/layers/",
        json=LAYER_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    layer_id = create.json()["id"]

    async def fake_fetch_ssl(service_url: str):
        raise ValueError(
            "服務的 SSL 憑證驗證失敗，無法新增此圖層：[SSL: CERTIFICATE_VERIFY_FAILED]"
        )

    monkeypatch.setattr(layer_service, "_fetch_legend_from_service", fake_fetch_ssl)

    resp = await client.patch(
        f"/api/v1/layers/{layer_id}",
        json={"name": "嘗試更新"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "SSL" in resp.json()["detail"]


def test_strip_empty_legend_items_filters_empty_labels():
    layers = [
        {"layerId": 0, "layerName": "World Imagery", "legend": [{"label": "", "imageData": "abc"}]},
        {"layerId": 1, "layerName": "Cities", "legend": [{"label": "City", "imageData": "xyz"}]},
    ]
    result = layer_service._strip_empty_legend_items(layers)
    assert len(result) == 1
    assert result[0]["layerId"] == 1


def test_strip_empty_legend_items_all_empty_returns_empty_list():
    layers = [
        {"layerId": 0, "layerName": "World Imagery", "legend": [{"label": "", "imageData": "abc"}]},
        {
            "layerId": 1,
            "layerName": "Low Resolution",
            "legend": [{"label": "  ", "imageData": "xyz"}],
        },
    ]
    result = layer_service._strip_empty_legend_items(layers)
    assert result == []


def test_strip_empty_legend_items_keeps_meaningful_items():
    layers = [
        {
            "layerId": 0,
            "layerName": "Cities",
            "legend": [
                {"label": "", "imageData": "blank"},
                {"label": "Major City", "imageData": "circle"},
            ],
        }
    ]
    result = layer_service._strip_empty_legend_items(layers)
    assert len(result) == 1
    assert len(result[0]["legend"]) == 1
    assert result[0]["legend"][0]["label"] == "Major City"
