# GIS 可視化決策平台 — 後端

FastAPI + SQLAlchemy 2.0 async + MySQL 後端，提供 RESTful API 給前端，管理 ArcGIS 圖層設定（CRUD）與 JWT 認證。

## 技術棧

- **框架**：FastAPI
- **語言**：Python 3.11+
- **資料庫**：MySQL 8.0
- **ORM**：SQLAlchemy 2.0（async）
- **Migration**：Alembic
- **認證**：python-jose（JWT）+ passlib（bcrypt）
- **驗證**：Pydantic v2
- **測試**：pytest + pytest-asyncio + httpx（AsyncClient）

## 本機開發

```bash
# 1. 建立虛擬環境並安裝依賴
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt

# 2. 建立 .env.local（複製範本後填入 MySQL 連線資訊）
cp .env.example .env.local

# 3. 執行 migration
alembic upgrade head

# 4. 初始化範例資料
python seed.py

# 5. 啟動開發伺服器
uvicorn app.main:app --reload
```

伺服器啟動後：
- API：http://localhost:8000/api/v1
- Swagger UI：http://localhost:8000/docs

## 環境變數

複製 `.env.example` 為 `.env.local` 並填寫：

```env
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/gis_platform
SECRET_KEY=your-random-secret-key
CORS_ORIGINS=http://localhost:5173
```

## 測試

```bash
pytest                          # 跑所有測試
pytest --cov=app tests/         # 含覆蓋率
pytest -v tests/test_layers.py  # 只跑圖層測試
```

測試使用 SQLite in-memory，不需要 MySQL。

## API 端點

| 方法 | 路徑 | 說明 | 權限 |
|---|---|---|---|
| POST | /api/v1/auth/login | 登入，取得 JWT | 公開 |
| POST | /api/v1/auth/refresh | 更新 access token | 公開 |
| GET | /api/v1/layers | 取得圖層列表（支援分頁/搜尋） | 登入 |
| POST | /api/v1/layers | 新增圖層 | Admin |
| PATCH | /api/v1/layers/{id} | 更新圖層 | Admin |
| DELETE | /api/v1/layers/{id} | 刪除圖層 | Admin |

## Migration

```bash
# 新增 migration
alembic revision --autogenerate -m "描述變更"

# 執行所有 migration
alembic upgrade head

# 回滾一步
alembic downgrade -1
```
