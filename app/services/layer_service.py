import json
import ssl
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from httpx import AsyncClient, ConnectError, HTTPError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.layer import Layer
from app.schemas.layer import LayerCreate, LayerUpdate


async def get_all_layers(db: AsyncSession) -> list[Layer]:
    result = await db.execute(select(Layer).order_by(Layer.sort_order))
    return list(result.scalars().all())


async def get_layer(db: AsyncSession, layer_id: int) -> Layer | None:
    return await db.get(Layer, layer_id)


def _build_legend_url(service_url: str) -> tuple[str, int | None]:
    """
    Build legend endpoint URL and extract layer_id.
    
    Examples:
    - Input: https://...MapServer/0
      Output: (https://...MapServer/legend, 0)
    - Input: https://...MapServer
      Output: (https://...MapServer/legend, None)
    """
    parsed = urlparse(service_url)
    path = parsed.path.rstrip("/")
    
    # Try to extract layer_id from the end of path
    parts = path.split("/")
    layer_id = None
    if parts[-1].isdigit():
        layer_id = int(parts[-1])
        path = "/".join(parts[:-1])  # Remove layer_id
    
    if not path.endswith("/legend"):
        path = f"{path}/legend"
    
    query = dict(parse_qsl(parsed.query))
    query["f"] = "json"
    legend_url = urlunparse(parsed._replace(path=path, query=urlencode(query, doseq=True)))
    return legend_url, layer_id


def _is_feature_server(url: str) -> bool:
    return "/FeatureServer" in url


async def _fetch_renderer_from_feature_server(service_url: str) -> dict:
    url = service_url.rstrip("/") + "?f=json"
    async with AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
        except ConnectError as exc:
            if isinstance(exc.__cause__, ssl.SSLError):
                raise ValueError(
                    f"服務的 SSL 憑證驗證失敗，無法新增此圖層：{exc.__cause__}"
                ) from exc
            raise ValueError(
                f"failed to fetch FeatureServer layer from {url}: {exc}"
            ) from exc
        except HTTPError as exc:
            raise ValueError(
                f"failed to fetch FeatureServer layer from {url}: {exc}"
            ) from exc

    if not isinstance(payload, dict):
        raise ValueError("FeatureServer layer endpoint returned unexpected format")

    if "error" in payload:
        raise ValueError(
            f"FeatureServer layer returned error: {payload['error']}"
        )

    drawing_info = payload.get("drawingInfo")
    if not isinstance(drawing_info, dict):
        raise ValueError("FeatureServer layer is missing drawingInfo")

    renderer = drawing_info.get("renderer")
    if not isinstance(renderer, dict):
        raise ValueError("FeatureServer layer is missing drawingInfo.renderer")

    return renderer


def _strip_empty_legend_items(layers: list[dict]) -> list[dict]:
    result = []
    for layer in layers:
        meaningful = [
            item for item in layer.get("legend", [])
            if item.get("label", "").strip()
        ]
        if meaningful:
            result.append({**layer, "legend": meaningful})
    return result


async def _fetch_legend_from_map_server(service_url: str) -> list[dict]:
    legend_url, layer_id = _build_legend_url(service_url)
    async with AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.get(legend_url)
            resp.raise_for_status()
            payload = resp.json()
        except ConnectError as exc:
            if isinstance(exc.__cause__, ssl.SSLError):
                raise ValueError(
                    f"服務的 SSL 憑證驗證失敗，無法新增此圖層：{exc.__cause__}"
                ) from exc
            raise ValueError(
                f"failed to fetch ArcGIS legend from {legend_url}: {exc}"
            ) from exc
        except HTTPError as exc:
            raise ValueError(
                f"failed to fetch ArcGIS legend from {legend_url}: {exc}"
            ) from exc

    if not isinstance(payload, dict):
        raise ValueError("ArcGIS legend endpoint returned unexpected response format")

    layers = payload.get("layers")
    if not isinstance(layers, list):
        raise ValueError(
            "ArcGIS legend endpoint response is missing a valid 'layers' array"
        )

    if layer_id is not None:
        filtered = [l for l in layers if l.get("layerId") == layer_id]
        if not filtered:
            raise ValueError(
                f"layer_id {layer_id} not found in legend response from {legend_url}"
            )
        return _strip_empty_legend_items(filtered)

    return _strip_empty_legend_items(layers)


async def _fetch_legend_from_service(service_url: str) -> list[dict] | dict:
    if _is_feature_server(service_url):
        return await _fetch_renderer_from_feature_server(service_url)
    return await _fetch_legend_from_map_server(service_url)


async def create_layer(db: AsyncSession, data: LayerCreate) -> Layer:
    layer_data = data.model_dump(exclude={"legend"})
    layer_data["renderer_json"] = json.dumps(
        await _fetch_legend_from_service(layer_data["service_url"]),
        ensure_ascii=False,
    )
    layer = Layer(**layer_data)
    db.add(layer)
    await db.commit()
    await db.refresh(layer)
    return layer


async def update_layer(db: AsyncSession, layer_id: int, data: LayerUpdate) -> Layer | None:
    layer = await db.get(Layer, layer_id)
    if not layer:
        return None
    updates = data.model_dump(exclude_unset=True, exclude={"legend"})
    service_url = updates.get("service_url", layer.service_url)
    updates["renderer_json"] = json.dumps(
        await _fetch_legend_from_service(service_url),
        ensure_ascii=False,
    )
    for field, value in updates.items():
        setattr(layer, field, value)
    await db.commit()
    await db.refresh(layer)
    return layer


async def delete_layer(db: AsyncSession, layer_id: int) -> None:
    layer = await db.get(Layer, layer_id)
    if layer:
        await db.delete(layer)
        await db.commit()
