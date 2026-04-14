from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.layer import Layer
from app.schemas.layer import LayerCreate, LayerUpdate


async def get_all_layers(db: AsyncSession) -> list[Layer]:
    result = await db.execute(select(Layer).order_by(Layer.sort_order))
    return list(result.scalars().all())


async def get_layer(db: AsyncSession, layer_id: int) -> Layer | None:
    return await db.get(Layer, layer_id)


async def create_layer(db: AsyncSession, data: LayerCreate) -> Layer:
    layer = Layer(**data.model_dump())
    db.add(layer)
    await db.commit()
    await db.refresh(layer)
    return layer


async def update_layer(db: AsyncSession, layer_id: int, data: LayerUpdate) -> Layer | None:
    layer = await db.get(Layer, layer_id)
    if not layer:
        return None
    updates = data.model_dump(exclude_unset=True)
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
