import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Layer(Base):
    __tablename__ = "layers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    service_url: Mapped[str] = mapped_column(String(500), nullable=False)
    layer_type: Mapped[str] = mapped_column(String(20), nullable=False)  # feature | tile
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    opacity: Mapped[float] = mapped_column(Float, default=1.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    renderer_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
