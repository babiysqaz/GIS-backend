from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.layer import LayerCreate, LayerResponse, LayerUpdate
from app.services import layer_service

router = APIRouter(prefix="/layers", tags=["layers"])


@router.get("/", response_model=list[LayerResponse])
async def list_layers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await layer_service.get_all_layers(db)


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
