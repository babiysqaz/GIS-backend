"""
初始資料腳本 — 建立 admin 帳號與範例 ArcGIS 圖層。

執行方式：
  # 本機開發
  python seed.py

  # Docker 環境
  docker compose exec backend python seed.py
"""

import asyncio
import urllib.parse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.layer import Layer
from app.models.user import User, UserRole
from app.schemas.layer import LayerCreate
from app.services import layer_service
from app.services.auth_service import hash_password

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

DEMO_USERS = [
    {
        "email": "admin@example.com",
        "password": "123456",
        "role": UserRole.ADMIN,
    },
    {
        "email": "user@example.com",
        "password": "123456",
        "role": UserRole.USER,
    },
]

_ARCGIS = "https://services3.arcgis.com/pKves1c0n6gyoHMM/arcgis/rest/services"


def _svc(name: str) -> str:
    return f"{_ARCGIS}/{urllib.parse.quote(name, safe='')}/FeatureServer/0"


DEMO_LAYERS = [
    {
        "name": "世界衛星影像",
        "description": "Esri World Imagery 高解析度衛星底圖",
        "service_url": "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer",
        "layer_type": "tile",
        "visible": True,
        "opacity": 1.0,
        "sort_order": 0,
    },
    {
        "name": "商業表燈用電量",
        "description": "2015年表燈營業用電量空間分布",
        "service_url": _svc("01_表燈營業用_2015"),
        "visible": True,
        "opacity": 0.8,
        "sort_order": 1,
    },
    {
        "name": "PM2.5污染分布",
        "description": "全台PM2.5細懸浮微粒污染分布",
        "service_url": _svc("10版PM25"),
        "visible": True,
        "opacity": 1.0,
        "sort_order": 2,
    },
    {
        "name": "焚化爐分布",
        "description": "全台焚化爐位置及未設置焚化爐縣市統計",
        "service_url": _svc("全臺焚化爐位置與未設置焚化爐縣市圖_WFL1"),
        "visible": True,
        "opacity": 1.0,
        "sort_order": 3,
    },
    {
        "name": "NOx氮氧化物排放",
        "description": "全台NOx氮氧化物排放量空間分布",
        "service_url": _svc("10版NOx"),
        "visible": False,
        "opacity": 1.0,
        "sort_order": 4,
    },
    {
        "name": "NMHC碳氫化合物排放",
        "description": "非甲烷碳氫化合物（NMHC）排放空間分布",
        "service_url": _svc("10版NMHC"),
        "visible": False,
        "opacity": 1.0,
        "sort_order": 5,
    },
    {
        "name": "風能資源潛力",
        "description": "全台各地區風能資源潛力評估",
        "service_url": _svc("風能資源量"),
        "visible": False,
        "opacity": 1.0,
        "sort_order": 6,
    },
    {
        "name": "縣市再生能源裝置容量",
        "description": "106年縣市別再生能源裝置容量統計",
        "service_url": _svc("106年_縣市再生能源"),
        "visible": False,
        "opacity": 1.0,
        "sort_order": 7,
    },
    {
        "name": "PM2.5歷年趨勢",
        "description": "102至104年PM2.5濃度時序變化分析",
        "service_url": _svc("102_104_PM2_5"),
        "visible": False,
        "opacity": 1.0,
        "sort_order": 8,
    },
]


async def seed_users(db: AsyncSession) -> None:
    for u in DEMO_USERS:
        result = await db.execute(select(User).where(User.email == u["email"]))
        if result.scalar_one_or_none():
            print(f"  [skip] user {u['email']} already exists")
            continue
        user = User(
            email=u["email"],
            hashed_password=hash_password(u["password"]),
            role=u["role"],
            is_active=True,
        )
        db.add(user)
        print(f"  [add]  user {u['email']} ({u['role'].value})")
    await db.commit()


async def seed_layers(db: AsyncSession) -> None:
    for layer in DEMO_LAYERS:
        result = await db.execute(select(Layer).where(Layer.service_url == layer["service_url"]))
        if result.scalar_one_or_none():
            print(f"  [skip] layer '{layer['name']}' already exists")
            continue
        try:
            await layer_service.create_layer(db, LayerCreate(**layer))
            print(f"  [add]  layer '{layer['name']}'")
        except ValueError as e:
            print(f"  [warn] layer '{layer['name']}': {e}")


async def main() -> None:
    print("=== Seeding database ===")
    async with SessionLocal() as db:
        print("Users:")
        await seed_users(db)
        print("Layers:")
        await seed_layers(db)
    print("=== Done ===")
    print()
    print("Demo accounts:")
    for u in DEMO_USERS:
        print(f"  {u['email']}  /  {u['password']}  ({u['role'].value})")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
