from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.layer import LayerCreate, LayerResponse, LayerUpdate, SortOrderItem
from app.services import layer_service

router = APIRouter(prefix="/layers", tags=["layers"])


@router.get("/all", response_model=list[LayerResponse])
async def list_all_layers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """回傳所有圖層（不分頁），供地圖前台使用。"""
    return await layer_service.get_all_layers(db)


@router.get("/", response_model=PaginatedResponse[LayerResponse])
async def list_layers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="依名稱或描述模糊搜尋"),
    layer_type: str | None = Query(None, pattern="^(feature|tile)$"),
    visible: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """回傳分頁圖層列表，支援搜尋與篩選，供後台管理使用。"""
    items, total = await layer_service.get_layers_paginated(
        db, page=page, size=size, search=search, layer_type=layer_type, visible=visible
    )
    return PaginatedResponse(items=items, total=total, page=page, size=size)


@router.post("/", response_model=LayerResponse, status_code=status.HTTP_201_CREATED)
async def create_layer(
    data: LayerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        return await layer_service.create_layer(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/sort-order", status_code=status.HTTP_204_NO_CONTENT)
async def batch_update_sort_order(
    items: list[SortOrderItem],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await layer_service.batch_update_sort_order(db, [item.model_dump() for item in items])


@router.patch("/{layer_id}", response_model=LayerResponse)
async def update_layer(
    layer_id: int,
    data: LayerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        layer = await layer_service.update_layer(db, layer_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return layer


@router.delete("/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    layer = await layer_service.get_layer(db, layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    await layer_service.delete_layer(db, layer_id)
