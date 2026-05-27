import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.schemas.common import BaseAPIModel


class LayerBase(BaseAPIModel):
    name: str
    description: str = ""
    service_url: str
    layer_type: Literal["feature", "tile"]
    visible: bool = True
    opacity: float = 1.0
    sort_order: int = 0

    @field_validator("opacity")
    @classmethod
    def opacity_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("opacity must be between 0.0 and 1.0")
        return v


class LayerCreate(LayerBase):
    pass


class LayerUpdate(BaseAPIModel):
    name: str | None = None
    description: str | None = None
    service_url: str | None = None
    layer_type: Literal["feature", "tile"] | None = None
    visible: bool | None = None
    opacity: float | None = None
    sort_order: int | None = None

    @field_validator("opacity")
    @classmethod
    def opacity_range(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("opacity must be between 0.0 and 1.0")
        return v


class LayerResponse(LayerBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
