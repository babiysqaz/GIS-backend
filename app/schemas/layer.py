import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import BaseAPIModel


class LegendItem(BaseAPIModel):
    label: str | None = None
    url: str | None = None
    image_data: str | None = None
    content_type: str | None = None
    height: int | None = None
    width: int | None = None


class LegendLayer(BaseAPIModel):
    layer_id: int
    layer_name: str
    layer_type: str | None = None
    min_scale: int | None = None
    max_scale: int | None = None
    legend: list[LegendItem] = Field(default_factory=list)


class LayerBase(BaseAPIModel):
    name: str
    description: str = ""
    service_url: str
    visible: bool = True
    opacity: float = 1.0
    legend: list[LegendLayer] | dict = Field(default_factory=list)

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
    visible: bool | None = None
    opacity: float | None = None
    legend: list[LegendLayer] | dict | None = None

    @field_validator("opacity")
    @classmethod
    def opacity_range(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("opacity must be between 0.0 and 1.0")
        return v


class SortOrderItem(BaseAPIModel):
    id: int
    sort_order: int


class LayerResponse(LayerBase):
    id: int
    layer_type: Literal["feature", "tile"]
    sort_order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
