from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


def to_camel(snake_str: str) -> str:
    """將 snake_case 轉換為 camelCase"""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class BaseAPIModel(BaseModel):
    """基礎 API 模型，自動處理 camelCase 和 snake_case 轉換"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # 同時接受欄位名稱與別名
        from_attributes=True,   # 從 ORM 物件讀取屬性
    )


class PaginatedResponse(BaseAPIModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
