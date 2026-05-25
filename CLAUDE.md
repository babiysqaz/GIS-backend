# GIS 可視化決策平台 — 後端

## 專案概覽

提供 RESTful API 給前端，管理圖層設定資料（CRUD）與使用者認證（JWT）。
地圖渲染由前端直接透過 ArcGIS JS API 完成，後端**不需要**代理 ArcGIS 請求。

**Repo:** `https://github.com/babiysqaz/GIS-backend`
**API 前綴:** `/api/v1`
**Python 版本:** 3.11+

---

## 技術棧

| 層級 | 套件 |
|---|---|
| 框架 | FastAPI |
| 語言 | Python 3.11+ |
| 資料庫 | MySQL 8.0 |
| ORM | SQLAlchemy 2.0（async） |
| Migration | Alembic |
| 認證 | python-jose（JWT） + passlib（bcrypt） |
| 資料驗證 | Pydantic v2 |
| 測試 | pytest + pytest-asyncio + httpx（AsyncClient） |
| 環境變數 | pydantic-settings |

---

## 目錄結構

```
app/
├── main.py                  # FastAPI app 建立、router 掛載、CORS 設定
├── config.py                # Settings（pydantic-settings）
├── database.py              # SQLAlchemy async engine + get_db
├── dependencies.py          # 共用 Depends（get_db、get_current_user、require_admin）
├── models/
│   ├── user.py              # User SQLAlchemy model
│   └── layer.py             # Layer SQLAlchemy model
├── schemas/
│   ├── user.py              # User Pydantic schemas
│   ├── layer.py             # Layer Pydantic schemas
│   └── common.py            # 共用 schema（PaginatedResponse 等）
├── routers/
│   ├── auth.py              # POST /auth/login、/auth/refresh
│   └── layers.py            # GET/POST/PATCH/DELETE /layers
├── services/
│   ├── auth_service.py      # JWT 建立/驗證、密碼雜湊
│   └── layer_service.py     # 圖層業務邏輯
└── migrations/
    └── versions/
alembic.ini
requirements.txt
.env.example
tests/
├── conftest.py
├── test_auth.py
└── test_layers.py
```

---

## 命名規範

- **檔案：** snake_case（`layer_service.py`）
- **Class：** PascalCase（`LayerCreate`、`LayerResponse`）
- **函式 / 變數：** snake_case（`get_current_user`、`layer_id`）
- **常數：** UPPER_SNAKE_CASE（`ACCESS_TOKEN_EXPIRE_MINUTES`）
- **Pydantic schema 後綴：**
  - `LayerCreate` — 建立時的輸入
  - `LayerUpdate` — 更新時的輸入（所有欄位 Optional，PATCH 語義）
  - `LayerResponse` — API 回傳給前端
- **Router 函式：** 動詞 + 名詞（`list_layers`、`create_layer`、`update_layer`、`delete_layer`）

---

## SQLAlchemy Model 規範

使用 SQLAlchemy 2.0 的 `DeclarativeBase` + `Mapped` 型別標注：

```python
# app/models/layer.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, Boolean, DateTime, Integer
from app.database import Base
import datetime

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
```

```python
# app/models/user.py
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
```

---

## Pydantic Schema 規範

```python
# app/schemas/layer.py
from pydantic import BaseModel
from typing import Literal
import datetime

class LayerBase(BaseModel):
    name: str
    description: str = ""
    service_url: str
    layer_type: Literal["feature", "tile"]
    visible: bool = True
    opacity: float = 1.0
    sort_order: int = 0

class LayerCreate(LayerBase):
    pass

class LayerUpdate(BaseModel):
    # 全部 Optional（PATCH 語義，只更新有傳的欄位）
    name: str | None = None
    description: str | None = None
    service_url: str | None = None
    layer_type: Literal["feature", "tile"] | None = None
    visible: bool | None = None
    opacity: float | None = None
    sort_order: int | None = None

class LayerResponse(LayerBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
```

---

## Router 規範

Router → Service → Model 三層；**禁止在 router 裡直接寫 DB 查詢**。

```python
# app/routers/layers.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user, require_admin
from app.schemas.layer import LayerCreate, LayerUpdate, LayerResponse
from app.services import layer_service
from app.models.user import User

router = APIRouter(prefix="/layers", tags=["layers"])

@router.get("/", response_model=list[LayerResponse])
async def list_layers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),   # 所有登入使用者可讀
):
    return await layer_service.get_all_layers(db)

@router.post("/", response_model=LayerResponse, status_code=status.HTTP_201_CREATED)
async def create_layer(
    data: LayerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),      # 僅管理員
):
    return await layer_service.create_layer(db, data)

@router.patch("/{layer_id}", response_model=LayerResponse)
async def update_layer(
    layer_id: int,
    data: LayerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    layer = await layer_service.update_layer(db, layer_id, data)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return layer

@router.delete("/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await layer_service.delete_layer(db, layer_id)
```

---

## JWT 認證規範

```python
# app/dependencies.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import verify_access_token
from app.models.user import User, UserRole

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = verify_access_token(credentials.credentials)  # 無效則拋 401
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or not found")
    return user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user
```

Token 設定（`app/config.py`）：
- `ACCESS_TOKEN_EXPIRE_MINUTES = 60`
- `REFRESH_TOKEN_EXPIRE_DAYS = 7`
- Algorithm: `HS256`

---

## Alembic Migration 規範

```bash
# 新增 migration（自動偵測 model 變動）
alembic revision --autogenerate -m "create_layers_table"

# 執行所有 migration
alembic upgrade head

# 回滾一步
alembic downgrade -1
```

**命名規則：** `動詞_描述`（snake_case）
- 建立資料表：`create_users_table`
- 新增欄位：`add_sort_order_to_layers`
- 修改欄位：`alter_service_url_length`

**禁止在 migration 檔案裡：**
- import 任何 `app.*` 模組
- 寫業務邏輯或條件判斷
- 直接操作資料（data migration 另開獨立 script）

---

## 標準 Response 格式

成功：直接回傳 Pydantic model，FastAPI 自動序列化。

錯誤：
```python
raise HTTPException(status_code=404, detail="Layer not found")
```

分頁（`app/schemas/common.py`）：
```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
```

---

## 環境變數

`.env.local`（不進版控）：
```
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/gis_platform
SECRET_KEY=change-this-to-a-random-secret
CORS_ORIGINS=http://localhost:5173
```

`.env.example`（進版控，作為範本）：
```
DATABASE_URL=
SECRET_KEY=
CORS_ORIGINS=
```

`app/config.py`：
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = {"env_file": ".env.local"}

settings = Settings()
```

---

## CORS 設定

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 開發指令

```bash
python -m venv .venv                     # 建立虛擬環境
.venv\Scripts\Activate.ps1               # 啟動虛擬環境
pip install -r requirements.txt          # 安裝依賴
uvicorn app.main:app --reload            # 啟動開發伺服器（port 8000）
alembic upgrade head                     # 執行所有 migration
pytest                                   # 跑測試
pytest --cov=app tests/                  # 含覆蓋率報告
```

---

## 禁止事項

- 禁止在 router 層直接寫 DB 查詢；業務邏輯放 `services/`
- 禁止 hardcode secret、密碼、API key；全部走環境變數
- 禁止在 API response 回傳 `hashed_password` 欄位
- 禁止使用同步 SQLAlchemy session；統一用 `AsyncSession`
- 禁止在 migration 裡 import app 模組或寫業務邏輯
- 禁止在後端建立任何 ArcGIS 相關路由或代理邏輯（前端直連 ArcGIS）
