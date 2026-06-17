import pytest
import respx
from httpx import ConnectError, Response

from app.services.layer_service import (
    _build_legend_url,
    _fetch_legend_from_map_server,
    _fetch_legend_from_service,
    _fetch_renderer_from_feature_server,
    _infer_layer_type,
    _is_feature_server,
    _is_ssl_error,
)

# ---------------------------------------------------------------------------
# _build_legend_url
# ---------------------------------------------------------------------------

def test_build_legend_url_extracts_layer_id():
    url, layer_id = _build_legend_url("https://example.com/MapServer/0")
    assert layer_id == 0
    assert url == "https://example.com/MapServer/legend?f=json"


def test_build_legend_url_without_layer_id():
    url, layer_id = _build_legend_url("https://example.com/MapServer")
    assert layer_id is None
    assert url == "https://example.com/MapServer/legend?f=json"


def test_build_legend_url_trailing_slash():
    url, layer_id = _build_legend_url("https://example.com/MapServer/2/")
    assert layer_id == 2
    assert url == "https://example.com/MapServer/legend?f=json"


# ---------------------------------------------------------------------------
# _is_ssl_error
# ---------------------------------------------------------------------------

def test_is_ssl_error_ssl_keyword():
    assert _is_ssl_error(ConnectError("ssl handshake failed")) is True


def test_is_ssl_error_certificate_keyword():
    assert _is_ssl_error(ConnectError("certificate verify failed")) is True


def test_is_ssl_error_other():
    assert _is_ssl_error(ConnectError("connection refused")) is False


# ---------------------------------------------------------------------------
# _is_feature_server / _infer_layer_type
# ---------------------------------------------------------------------------

def test_is_feature_server_true():
    assert _is_feature_server("https://example.com/FeatureServer/0") is True


def test_is_feature_server_false():
    assert _is_feature_server("https://example.com/MapServer/0") is False


def test_infer_layer_type_feature():
    assert _infer_layer_type("https://example.com/FeatureServer/0") == "feature"


def test_infer_layer_type_tile():
    assert _infer_layer_type("https://example.com/MapServer/0") == "tile"


# ---------------------------------------------------------------------------
# _fetch_legend_from_map_server
# ---------------------------------------------------------------------------

_MAP_LEGEND = {
    "layers": [
        {
            "layerId": 0,
            "layerName": "Cities",
            "legend": [{"label": "City", "imageData": "abc"}],
        }
    ]
}


@pytest.mark.asyncio
async def test_fetch_legend_map_server_success_with_layer_id():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            return_value=Response(200, json=_MAP_LEGEND)
        )
        result = await _fetch_legend_from_map_server("https://example.com/MapServer/0")
    assert len(result) == 1
    assert result[0]["layerId"] == 0


@pytest.mark.asyncio
async def test_fetch_legend_map_server_success_without_layer_id():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            return_value=Response(200, json=_MAP_LEGEND)
        )
        result = await _fetch_legend_from_map_server("https://example.com/MapServer")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_fetch_legend_map_server_layer_id_not_found():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            return_value=Response(200, json=_MAP_LEGEND)
        )
        with pytest.raises(ValueError, match="layer_id 99"):
            await _fetch_legend_from_map_server("https://example.com/MapServer/99")


@pytest.mark.asyncio
async def test_fetch_legend_map_server_ssl_error():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            side_effect=ConnectError("ssl certificate verify failed")
        )
        with pytest.raises(ValueError, match="SSL"):
            await _fetch_legend_from_map_server("https://example.com/MapServer/0")


@pytest.mark.asyncio
async def test_fetch_legend_map_server_connect_error():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            side_effect=ConnectError("connection refused")
        )
        with pytest.raises(ValueError, match="failed to fetch ArcGIS legend"):
            await _fetch_legend_from_map_server("https://example.com/MapServer/0")


@pytest.mark.asyncio
async def test_fetch_legend_map_server_http_error():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            return_value=Response(500)
        )
        with pytest.raises(ValueError, match="failed to fetch ArcGIS legend"):
            await _fetch_legend_from_map_server("https://example.com/MapServer/0")


@pytest.mark.asyncio
async def test_fetch_legend_map_server_invalid_response_format():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            return_value=Response(200, json=["not", "a", "dict"])
        )
        with pytest.raises(ValueError, match="unexpected response format"):
            await _fetch_legend_from_map_server("https://example.com/MapServer/0")


@pytest.mark.asyncio
async def test_fetch_legend_map_server_missing_layers_key():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            return_value=Response(200, json={"other": "data"})
        )
        with pytest.raises(ValueError, match="missing a valid 'layers'"):
            await _fetch_legend_from_map_server("https://example.com/MapServer/0")


# ---------------------------------------------------------------------------
# _fetch_renderer_from_feature_server
# ---------------------------------------------------------------------------

_FEATURE_RESPONSE = {
    "drawingInfo": {
        "renderer": {"type": "simple", "symbol": {"type": "esriSMS"}}
    }
}


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_success():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            return_value=Response(200, json=_FEATURE_RESPONSE)
        )
        result = await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")
    assert result["type"] == "simple"


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_ssl_error():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            side_effect=ConnectError("ssl certificate verify failed")
        )
        with pytest.raises(ValueError, match="SSL"):
            await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_connect_error():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            side_effect=ConnectError("connection refused")
        )
        with pytest.raises(ValueError, match="failed to fetch FeatureServer"):
            await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_http_error():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            return_value=Response(503)
        )
        with pytest.raises(ValueError, match="failed to fetch FeatureServer"):
            await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_error_in_payload():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            return_value=Response(200, json={"error": {"code": 400, "message": "Invalid layer"}})
        )
        with pytest.raises(ValueError, match="returned error"):
            await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_invalid_format():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            return_value=Response(200, json=["not", "a", "dict"])
        )
        with pytest.raises(ValueError, match="unexpected format"):
            await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_missing_drawing_info():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            return_value=Response(200, json={"type": "Feature"})
        )
        with pytest.raises(ValueError, match="missing drawingInfo"):
            await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")


@pytest.mark.asyncio
async def test_fetch_renderer_feature_server_missing_renderer():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            return_value=Response(200, json={"drawingInfo": {}})
        )
        with pytest.raises(ValueError, match=r"missing drawingInfo\.renderer"):
            await _fetch_renderer_from_feature_server("https://example.com/FeatureServer/0")


# ---------------------------------------------------------------------------
# _fetch_legend_from_service（routing 邏輯）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_legend_from_service_routes_feature_server():
    with respx.mock:
        respx.get("https://example.com/FeatureServer/0?f=json").mock(
            return_value=Response(200, json=_FEATURE_RESPONSE)
        )
        result = await _fetch_legend_from_service("https://example.com/FeatureServer/0")
    assert isinstance(result, dict)
    assert result["type"] == "simple"


@pytest.mark.asyncio
async def test_fetch_legend_from_service_routes_map_server():
    with respx.mock:
        respx.get("https://example.com/MapServer/legend?f=json").mock(
            return_value=Response(200, json=_MAP_LEGEND)
        )
        result = await _fetch_legend_from_service("https://example.com/MapServer/0")
    assert isinstance(result, list)
    assert result[0]["layerId"] == 0
